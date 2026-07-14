"""
LangGraph tools available to the HCP Interaction Agent.

Each tool is a thin wrapper around the database layer. The LLM (Groq
gemma2-9b-it) is used inside `log_interaction_tool` to turn unstructured
free text ("Met Dr. Smith, discussed Product X efficacy, positive
sentiment, shared brochure") into structured fields via entity
extraction, and inside `summarize_interaction_tool` to condense long
notes.
"""
import json
import os
from datetime import datetime
from typing import Optional

from langchain_core.tools import tool
from langchain_groq import ChatGroq
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import HCP, Interaction

GROQ_MODEL = os.getenv("GROQ_MODEL", "gemma2-9b-it")

_llm = ChatGroq(model=GROQ_MODEL, temperature=0)

EXTRACTION_PROMPT = """You are a life-sciences CRM assistant. Extract structured fields from a
field representative's free-text note about a Healthcare Professional (HCP) interaction.

Return ONLY valid JSON (no markdown fences, no commentary) with this exact shape:
{{
  "hcp_name": string,
  "interaction_type": one of ["Meeting", "Call", "Email", "Conference"],
  "topics_discussed": string,
  "materials_shared": [string],
  "samples_distributed": [string],
  "sentiment": one of ["Positive", "Neutral", "Negative"],
  "outcomes": string,
  "follow_up_actions": string
}}

If a field isn't mentioned, use an empty string or empty list. Never invent HCP names.

Note: {note}
"""


def _get_or_create_hcp(db: Session, name: str) -> HCP:
    hcp = db.query(HCP).filter(HCP.name.ilike(name.strip())).first()
    if not hcp:
        hcp = HCP(name=name.strip())
        db.add(hcp)
        db.commit()
        db.refresh(hcp)
    return hcp


@tool
def log_interaction_tool(note: str) -> str:
    """Log a new HCP interaction from a free-text note. Uses the LLM to extract
    HCP name, interaction type, topics discussed, materials/samples shared,
    sentiment, outcomes, and follow-up actions, then persists a new
    interaction record. Returns the created interaction as JSON."""
    resp = _llm.invoke(EXTRACTION_PROMPT.format(note=note))
    try:
        data = json.loads(resp.content.strip().strip("`").removeprefix("json"))
    except json.JSONDecodeError:
        data = {
            "hcp_name": "Unknown HCP",
            "interaction_type": "Meeting",
            "topics_discussed": note,
            "materials_shared": [],
            "samples_distributed": [],
            "sentiment": "Neutral",
            "outcomes": "",
            "follow_up_actions": "",
        }

    db = SessionLocal()
    try:
        hcp = _get_or_create_hcp(db, data.get("hcp_name") or "Unknown HCP")
        interaction = Interaction(
            hcp_id=hcp.id,
            interaction_type=data.get("interaction_type", "Meeting"),
            interaction_date=datetime.utcnow(),
            attendees=[],
            topics_discussed=data.get("topics_discussed", ""),
            materials_shared=data.get("materials_shared", []),
            samples_distributed=data.get("samples_distributed", []),
            sentiment=data.get("sentiment", "Neutral"),
            outcomes=data.get("outcomes", ""),
            follow_up_actions=data.get("follow_up_actions", ""),
            source="chat",
            raw_chat_text=note,
        )
        db.add(interaction)
        db.commit()
        db.refresh(interaction)
        return json.dumps({
            "id": interaction.id,
            "hcp_name": hcp.name,
            "interaction_type": interaction.interaction_type,
            "sentiment": interaction.sentiment,
            "topics_discussed": interaction.topics_discussed,
        })
    finally:
        db.close()


@tool
def edit_interaction_tool(interaction_id: str, field: str, new_value: str) -> str:
    """Edit a single field of an already-logged interaction. `field` must be
    one of: interaction_type, topics_discussed, sentiment, outcomes,
    follow_up_actions. `new_value` is the replacement text. Returns the
    updated interaction as JSON, or an error message if not found."""
    db = SessionLocal()
    try:
        interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
        if not interaction:
            return json.dumps({"error": f"No interaction found with id {interaction_id}"})
        allowed = {"interaction_type", "topics_discussed", "sentiment", "outcomes", "follow_up_actions"}
        if field not in allowed:
            return json.dumps({"error": f"Field '{field}' is not editable. Allowed: {sorted(allowed)}"})
        setattr(interaction, field, new_value)
        interaction.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(interaction)
        return json.dumps({"id": interaction.id, field: getattr(interaction, field), "status": "updated"})
    finally:
        db.close()


@tool
def summarize_interaction_tool(raw_text: str) -> str:
    """Summarize a long voice-note transcript or free-text interaction note
    into 2-3 concise sentences suitable for the 'Topics Discussed' field."""
    prompt = (
        "Summarize the following field rep note into 2-3 concise, factual "
        "sentences for a CRM 'Topics Discussed' field. No preamble.\n\n"
        f"Note: {raw_text}"
    )
    resp = _llm.invoke(prompt)
    return resp.content.strip()


@tool
def suggest_followups_tool(interaction_id: str) -> str:
    """Given a logged interaction, suggest 2-4 concrete follow-up actions
    (e.g. scheduling a meeting, sending literature, adding to an advisory
    board list) based on the topics discussed and outcomes."""
    db = SessionLocal()
    try:
        interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
        if not interaction:
            return json.dumps({"error": f"No interaction found with id {interaction_id}"})
        prompt = (
            "Based on this HCP interaction, suggest 2-4 short, specific "
            "follow-up actions as a JSON list of strings (no commentary).\n\n"
            f"Topics discussed: {interaction.topics_discussed}\n"
            f"Sentiment: {interaction.sentiment}\n"
            f"Outcomes: {interaction.outcomes}"
        )
        resp = _llm.invoke(prompt)
        try:
            suggestions = json.loads(resp.content.strip().strip("`").removeprefix("json"))
        except json.JSONDecodeError:
            suggestions = [line.strip("- ") for line in resp.content.strip().splitlines() if line.strip()]
        return json.dumps({"interaction_id": interaction_id, "suggestions": suggestions})
    finally:
        db.close()


@tool
def search_hcp_history_tool(hcp_name: str) -> str:
    """Look up the interaction history for a given HCP by name, returning a
    list of past interactions (date, type, sentiment, topics) so the rep or
    the agent has context before logging a new one."""
    db = SessionLocal()
    try:
        hcp = db.query(HCP).filter(HCP.name.ilike(f"%{hcp_name.strip()}%")).first()
        if not hcp:
            return json.dumps({"error": f"No HCP found matching '{hcp_name}'"})
        history = [
            {
                "id": i.id,
                "date": i.interaction_date.isoformat() if i.interaction_date else None,
                "type": i.interaction_type,
                "sentiment": i.sentiment,
                "topics": i.topics_discussed,
            }
            for i in sorted(hcp.interactions, key=lambda x: x.interaction_date or datetime.min, reverse=True)
        ]
        return json.dumps({"hcp_name": hcp.name, "history": history})
    finally:
        db.close()


ALL_TOOLS = [
    log_interaction_tool,
    edit_interaction_tool,
    summarize_interaction_tool,
    suggest_followups_tool,
    search_hcp_history_tool,
]
