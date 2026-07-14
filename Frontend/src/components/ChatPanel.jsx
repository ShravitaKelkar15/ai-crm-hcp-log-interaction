import React, { useRef, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { sendChatMessage } from "../redux/interactionSlice.js";

const SESSION_ID = "rep-session-1";

export default function ChatPanel() {
  const dispatch = useDispatch();
  const { chatMessages, chatStatus } = useSelector((state) => state.interaction);
  const [draft, setDraft] = useState("");
  const listRef = useRef(null);

  const handleSend = (e) => {
    e.preventDefault();
    if (!draft.trim()) return;
    dispatch(sendChatMessage({ message: draft, sessionId: SESSION_ID }));
    setDraft("");
    setTimeout(() => {
      listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
    }, 50);
  };

  return (
    <div className="panel chat-panel">
      <div className="chat-header">AI Assistant</div>
      <div className="chat-subtitle">Log interaction via chat</div>

      <div className="chat-messages" ref={listRef}>
        {chatMessages.length === 0 && (
          <div className="chat-bubble assistant">
            Log interaction details here (e.g., "Met Dr. Smith, discussed
            Product X efficacy, positive sentiment, shared brochure") or ask
            for help.
          </div>
        )}
        {chatMessages.map((m, i) => (
          <div key={i} className={`chat-bubble ${m.role}`}>
            {m.text}
          </div>
        ))}
        {chatStatus === "loading" && (
          <div className="chat-bubble assistant">Thinking...</div>
        )}
      </div>

      <form className="chat-input-row" onSubmit={handleSend}>
        <input
          placeholder="Describe interaction..."
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
        />
        <button type="submit" disabled={chatStatus === "loading"}>
          Log
        </button>
      </form>
    </div>
  );
}
