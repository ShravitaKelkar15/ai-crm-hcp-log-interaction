import React from "react";
import StructuredForm from "./components/StructuredForm.jsx";
import ChatPanel from "./components/ChatPanel.jsx";

export default function App() {
  return (
    <div className="app-shell">
      <div className="app-title">Log HCP Interaction</div>
      <div className="screen-grid">
        <StructuredForm />
        <ChatPanel />
      </div>
    </div>
  );
}
