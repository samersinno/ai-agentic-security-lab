from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langchain_core.messages import AIMessage
import os, subprocess
from ddgs import DDGS


# ---- State ----

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    retry_count: int


# ---- Tools (same logic as Week 2/3) ----

@tool
def web_search(query: str) -> str:
    """Search the web for current information."""
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=3))
    if not results:
        return "No results found."
    text = "\n".join(f"- {r['title']}: {r['body']}" for r in results)
    return text[:2000]

@tool
def run_code(code: str) -> str:
    """Run Python code in a sandboxed environment and return stdout."""
    dangerous = ["import os", "import subprocess", "import sys", "__import__", "open(", "eval(", "exec("]
    if any(p in code for p in dangerous):
        return "Error: code rejected by safety filter (contains disallowed pattern)."

    sandbox_dir = "/tmp/agent-sandbox"
    script_path = os.path.join(sandbox_dir, "script.py")
    with open(script_path, "w") as f:
        f.write(code)

    result = subprocess.run(
        ["docker", "run", "--rm", "--network", "none",
         "-v", f"{sandbox_dir}:/sandbox",
         "python:3.11-slim", "python", "/sandbox/script.py"],
        capture_output=True, text=True, timeout=30
    )
    output = result.stdout if result.returncode == 0 else f"Error: {result.stderr}"
    return output[:2000]

tools = [web_search, run_code]


# ---- Agent node ----

model = ChatAnthropic(model="claude-sonnet-4-6").bind_tools(tools)

def call_model(state: AgentState):
    response = model.invoke(state["messages"])
    return {"messages": [response]}


# ---- Routing: should we call a tool, or are we done? ----

def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return "end"


# ---- Routing: did the tool fail? Should we retry or give up? ----

def check_tool_result(state: AgentState):
    last_message = state["messages"][-1]
    if last_message.type == "tool" and "Error" in str(last_message.content):
        return {"retry_count": state.get("retry_count", 0) + 1}
    return {"retry_count": 0}

def route_after_tools(state: AgentState):
    if state.get("retry_count", 0) >= 3:
        return "give_up"
    return "agent"

def give_up(state: AgentState):
    return {"messages": [AIMessage(content="I tried this tool 3 times and kept hitting errors — stopping here rather than looping indefinitely. You may want to check the input manually.")]}


# ---- Build the graph ----

graph = StateGraph(AgentState)
graph.add_node("agent", call_model)
graph.add_node("tools", ToolNode(tools))
graph.add_node("check_result", check_tool_result)
graph.add_node("give_up", give_up)

graph.set_entry_point("agent")
graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
graph.add_edge("tools", "check_result")
graph.add_conditional_edges("check_result", route_after_tools, {"agent": "agent", "give_up": "give_up"})
graph.add_edge("give_up", END)

app = graph.compile()


# ---- Run it ----
# NOTE: this prompt is deliberately set to trigger the retry/give_up path for testing.
# After confirming give_up fires correctly, swap this back to a normal question.

result = app.invoke(
    {"messages": [("user", "What's 47293 * 8123, and who is the current Anthropic CEO? Use tools as needed.")]},
    config={"recursion_limit": 10}
)
for msg in result["messages"]:
    print(f"[{msg.type}] {msg.content}")
