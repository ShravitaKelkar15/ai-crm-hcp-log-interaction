from typing import List

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage, AIMessage
from sqlalchemy.orm import Session

from . import models, schemas
from .database import engine, get_db, SessionLocal
from .models import HCP, Interaction
from .agent.graph import hcp_agent_graph

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI-First CRM — HCP Module API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# in-memory per-session chat history (fine for an assignment/demo; swap for
# Redis or a DB table for production)
_chat_sessions: dict[str, list] = {}


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------- Structured form path ----------

@app.post("/interactions", response_model=schemas.InteractionOut)
def create_interaction(payload: schemas.InteractionCreate, db: Session = Depends(get_db)):
    hcp = db.query(HCP).filter(HCP.name.ilike(payload.hcp_name.strip())).first()
    if not hcp:
        hcp = HCP(name=payload.hcp_name.strip())
        db.add(hcp)
        db.commit()
        db.refresh(hcp)

    interaction = Interaction(
        hcp_id=hcp.id,
        interaction_type=payload.interaction_type,
        interaction_date=payload.interaction_date,
        attendees=payload.attendees,
        topics_discussed=payload.topics_discussed,
        materials_shared=payload.materials_shared,
        samples_distributed=payload.samples_distributed,
        sentiment=payload.sentiment,
        outcomes=payload.outcomes,
        follow_up_actions=payload.follow_up_actions,
        source="form",
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    return _to_out(interaction, hcp.name)


@app.get("/interactions", response_model=List[schemas.InteractionOut])
def list_interactions(db: Session = Depends(get_db)):
    interactions = db.query(Interaction).order_by(Interaction.created_at.desc()).all()
    return [_to_out(i, i.hcp.name) for i in interactions]


@app.put("/interactions/{interaction_id}", response_model=schemas.InteractionOut)
def update_interaction(interaction_id: str, payload: schemas.InteractionUpdate, db: Session = Depends(get_db)):
    interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(interaction, field, value)
    db.commit()
    db.refresh(interaction)
    return _to_out(interaction, interaction.hcp.name)


def _to_out(interaction: Interaction, hcp_name: str) -> schemas.InteractionOut:
    return schemas.InteractionOut(
        id=interaction.id,
        hcp_id=interaction.hcp_id,
        hcp_name=hcp_name,
        interaction_type=interaction.interaction_type,
        interaction_date=interaction.interaction_date,
        attendees=interaction.attendees or [],
        topics_discussed=interaction.topics_discussed,
        materials_shared=interaction.materials_shared or [],
        samples_distributed=interaction.samples_distributed or [],
        sentiment=interaction.sentiment,
        outcomes=interaction.outcomes,
        follow_up_actions=interaction.follow_up_actions,
        source=interaction.source,
        created_at=interaction.created_at,
        updated_at=interaction.updated_at,
    )


# ---------- Conversational (LangGraph agent) path ----------

@app.post("/chat", response_model=schemas.ChatResponse)
def chat(payload: schemas.ChatRequest):
    history = _chat_sessions.setdefault(payload.session_id, [])
    history.append(HumanMessage(content=payload.message))

    result = hcp_agent_graph.invoke({"messages": history})
    messages = result["messages"]
    _chat_sessions[payload.session_id] = messages

    tool_calls_used = [
        call["name"]
        for m in messages
        if isinstance(m, AIMessage) and getattr(m, "tool_calls", None)
        for call in m.tool_calls
    ]

    final_reply = messages[-1].content if isinstance(messages[-1], AIMessage) else ""
    return schemas.ChatResponse(reply=final_reply, tool_calls=tool_calls_used, interaction=None)
