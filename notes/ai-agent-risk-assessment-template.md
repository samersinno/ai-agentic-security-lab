# AI Agent Risk Assessment Template

*A working template for evaluating agentic AI systems before deployment — developed through hands-on testing, not just theory.*

---

## How to use this template

Walk through each section with whoever owns the agent being assessed (a developer, a product owner, a client's technical lead). Each question below is grounded in something concrete — either a specific real vulnerability, or a specific thing observed while building and testing agents hands-on. That grounding is what separates a useful assessment from a generic checklist.

---

## 1. Tool Inventory

**Question:** What tools/functions does this agent have access to? For each one — is it read-only, or does it have real-world side effects (write, delete, send, purchase, execute)?

**Why this matters:** the *category* of tool determines the ceiling on what can go wrong. A read-only search tool being misused is a minor annoyance. A code-execution tool or a file-write tool being misused is a real incident.

| Tool name | Read-only or side effects? | Worst-case action it could take |
|---|---|---|
| e.g. `run_code` | Side effects (executes code) | Full compromise of whatever it can reach — must be sandboxed |
| e.g. `read_file` | Read-only, but sensitive | Exposure of anything on the accessible filesystem |

---

## 2. Blast Radius

**Question:** If this agent's output were fully manipulated by an attacker (via prompt injection or otherwise), what's the worst realistic outcome given its *current* tool access?

**Why this matters — grounded in real testing:** a `read_file` tool with zero restrictions was tested against three escalating prompt-injection attempts. All three failed — but that success depended entirely on the model's own judgment, not on any actual limit in the tool. Had a fourth, more sophisticated attempt succeeded, the tool would have read anything the process had filesystem access to. **The blast radius of a tool is determined by its own limits, not by how well the model currently resists attacks against it.**

**How to answer:** assume the worst-case injection succeeds. Trace forward — what could actually happen? If the answer involves real data exposure, financial actions, or irreversible changes, that tool needs independent restrictions regardless of model performance in testing.

---

## 3. Human-in-the-Loop Coverage

**Question:** Which actions does this agent take *without* requiring human approval? Should any of them require it?

**Why this matters:** a production agent taking real actions (sending communications, modifying records, making purchases) needs an explicit answer to "does a human confirm this first?" for each action category — not an implicit assumption either way.

**How to answer:** list every distinct action type the agent can take. For each, mark: fully autonomous / requires confirmation / not permitted at all.

---

## 4. Input Provenance

**Question:** Does the agent process any content it didn't generate itself and that wasn't directly typed by a trusted user — web pages, emails, uploaded files, API responses, log data?

**Why this matters — grounded in real testing:** this is the exact mechanism prompt injection exploits. Testing demonstrated the difference between *direct* injection (an obvious command typed into a prompt) and *indirect* injection (a malicious instruction hidden inside content the agent processes, e.g. CSS-hidden text in a webpage). The second category is meaningfully harder to defend against and easier to miss, because a human skimming the same content wouldn't see anything hidden with `display:none`.

**How to answer:** for every content source the agent touches that isn't directly typed by a trusted human, ask: is this source fully trusted? If not, treat all content from it as potentially containing hidden instructions, not just data.

---

## 5. Input Sanitization

**Question:** Are tool arguments validated or constrained before execution, or does whatever the model outputs get run as-is?

**Why this matters — grounded in real testing:** a code-execution tool used a simple denylist (blocking strings like `"import os"`) as a first-pass filter, with real protection coming from Docker sandboxing (`--network none`, isolated filesystem). Testing showed the denylist is trivially bypassable — it caught obvious cases but had no understanding of what the code actually did. **A denylist is a cheap first layer, never the actual security boundary.**

**How to answer:** identify what the *real* boundary is for each tool — not the friendliest-looking check, but the thing that would actually stop a determined attempt. If the only boundary is "the model probably won't generate something bad," that's not a boundary.

---

## 6. Credential Scope

**Question:** What credentials or permissions do the agent's tools hold? Are they scoped to the minimum needed, or broader?

**Why this matters:** this is the practical form of "excessive agency" (OWASP LLM06:2025) — giving a system more permission than its task requires. An agent that only ever needs to read one specific file should not have unrestricted filesystem access.

**How to answer:** for each credential the agent's tools use, ask: could this task be accomplished with a narrower version of this credential? If yes, that's a gap.

---

## 7. Logging & Auditability

**Question:** Is every tool call logged in a way a human can review after the fact — what was called, with what arguments, and what came back?

**Why this matters — grounded in real testing:** full tool-call tracing made it possible to catch subtle issues — a model producing a confidently wrong arithmetic answer, and a model fabricating a plausible-sounding explanation for something it hadn't actually observed. Without that trace, both would have gone unnoticed, because the final answers still *sounded* correct.

**How to answer:** confirm whether the production system retains equivalent visibility, or whether it only shows the user the final output — which hides exactly this class of failure.

---

## Summary scoring (optional client-facing view)

| Category | Low Risk | Medium Risk | High Risk |
|---|---|---|---|
| Tool Inventory | All read-only | Mixed, well-scoped | Unrestricted side-effect tools |
| Blast Radius | Minimal worst case | Contained but meaningful | Significant data/system exposure |
| Human-in-the-Loop | High-risk actions confirmed | Some gaps | Fully autonomous on consequential actions |
| Input Provenance | No untrusted content | Some, reviewed sources | Arbitrary external content |
| Input Sanitization | Independent validation | Basic filtering | Relies solely on model behavior |
| Credential Scope | Minimum necessary | Broader than needed | Broad/admin-level access |
| Logging | Full trace retained | Partial | Final output only |

---

*Developed as part of a hands-on agentic AI + cybersecurity learning program, grounded in direct testing of prompt injection, tool misuse, and guardrail effectiveness against a self-built agent stack (LangGraph, sandboxed code execution, web search, file access).*
