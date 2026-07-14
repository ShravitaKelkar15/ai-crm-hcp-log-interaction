"""
The LangGraph agent that powers the chat side of the Log Interaction
Screen.

Role of the agent: it sits between the free-text chat box and the
structured database. A field rep can type something like "Met Dr. Smith,
discussed Product X efficacy, positive sentiment, shared brochure" and the
agent decides which tool(s) to call - typically `log_interaction_tool` to
extract + persist structured fields, but it can also pull up an HCP's
history before logging, edit a field the rep corrects ("actually make
that neutral, not positive"), summarize a long voice-note transcript, or
suggest follow-ups after logging. The graph loops between an LLM
"agent" node and a "tools" node until the LLM responds without any
further tool calls, at which point the final answer is returned to the
UI.
"""
import os
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from .tools import ALL_TOOLS

GROQ_MODEL = os.getenv("GROQ_MODEL", "gemma2-9b-it")

SYSTEM_PROMPT = SystemMessage(content=(
    "You are the CRM assistant embedded in the HCP 'Log Interaction' screen "
    "for a pharma field representative. You have five tools: "
    "log_interaction_tool (extract + save a new interaction from free text), "
    "edit_interaction_tool (correct a field on an already-logged interaction), "
    "summarize_interaction_tool (condense a long note), "
    "suggest_followups_tool (propose next steps for a logged interaction), and "
    "search_hcp_history_tool (look up an HCP's past interactions). "
    "When the rep describes an interaction, call log_interaction_tool. "
    "When they correct something already logged, call edit_interaction_tool. "
    "Always confirm back to the rep in one short, plain-English sentence "
    "after a tool call - no markdown, no jargon."
))


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


llm = ChatGroq(model=GROQ_MODEL, temperature=0)
llm_with_tools = llm.bind_tools(ALL_TOOLS)


def agent_node(state: AgentState) -> AgentState:
    messages = [SYSTEM_PROMPT] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


def should_continue(state: AgentState) -> str:
    last_message = state["messages"][-1]
    if getattr(last_message, "tool_calls", None):
        return "tools"
    return END


tool_node = ToolNode(ALL_TOOLS)

workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", tool_node)
workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
workflow.add_edge("tools", "agent")

hcp_agent_graph = workflow.compile()
