from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
import os, subprocess
from ddgs import DDGS


# ---- State ----

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


# ---- Tools (same logic as Week 2, wrapped for LangGraph) ----

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


# ---- Routing logic (conditional edge) ----

def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return "end"


# ---- Build the graph ----

graph = StateGraph(AgentState)
graph.add_node("agent", call_model)
graph.add_node("tools", ToolNode(tools))
graph.set_entry_point("agent")
graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
graph.add_edge("tools", "agent")

app = graph.compile()


# ---- Run it ----

result = app.invoke({"messages": [("user", "What's 47293 * 8123, and who is the current Anthropic CEO? Use tools as needed.")]})

for msg in result["messages"]:
    print(f"[{msg.type}] {msg.content}")
