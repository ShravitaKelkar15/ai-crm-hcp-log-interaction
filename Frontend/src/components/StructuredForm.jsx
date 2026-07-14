import React from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  updateField,
  submitInteraction,
} from "../redux/interactionSlice.js";

export default function StructuredForm() {
  const dispatch = useDispatch();
  const { form, submitStatus, suggestedFollowups } = useSelector(
    (state) => state.interaction
  );

  const handleChange = (field) => (e) => {
    dispatch(updateField({ field, value: e.target.value }));
  };

  const handleListChange = (field) => (e) => {
    const value = e.target.value.split(",").map((v) => v.trim()).filter(Boolean);
    dispatch(updateField({ field, value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    dispatch(submitInteraction(form));
  };

  return (
    <div className="panel">
      <div className="panel-title">Interaction Details</div>
      <form onSubmit={handleSubmit}>
        <div className="field-row">
          <div className="field">
            <label>HCP Name</label>
            <input
              placeholder="Search or select HCP..."
              value={form.hcp_name}
              onChange={handleChange("hcp_name")}
              required
            />
          </div>
          <div className="field">
            <label>Interaction Type</label>
            <select value={form.interaction_type} onChange={handleChange("interaction_type")}>
              <option>Meeting</option>
              <option>Call</option>
              <option>Email</option>
              <option>Conference</option>
            </select>
          </div>
        </div>

        <div className="field-row">
          <div className="field">
            <label>Date & Time</label>
            <input
              type="datetime-local"
              value={form.interaction_date}
              onChange={handleChange("interaction_date")}
            />
          </div>
          <div className="field">
            <label>Attendees</label>
            <input
              placeholder="Enter names, comma separated..."
              value={form.attendees.join(", ")}
              onChange={handleListChange("attendees")}
            />
          </div>
        </div>

        <div className="field">
          <label>Topics Discussed</label>
          <textarea
            placeholder="Enter key discussion points..."
            value={form.topics_discussed}
            onChange={handleChange("topics_discussed")}
          />
        </div>

        <div className="field-row" style={{ marginTop: 14 }}>
          <div className="field">
            <label>Materials Shared</label>
            <input
              placeholder="Comma separated..."
              value={form.materials_shared.join(", ")}
              onChange={handleListChange("materials_shared")}
            />
          </div>
          <div className="field">
            <label>Samples Distributed</label>
            <input
              placeholder="Comma separated..."
              value={form.samples_distributed.join(", ")}
              onChange={handleListChange("samples_distributed")}
            />
          </div>
        </div>

        <div className="field">
          <label>Observed / Inferred HCP Sentiment</label>
        </div>
        <div className="sentiment-row">
          {["Positive", "Neutral", "Negative"].map((s) => (
            <label key={s}>
              <input
                type="radio"
                name="sentiment"
                value={s}
                checked={form.sentiment === s}
                onChange={handleChange("sentiment")}
              />
              {s}
            </label>
          ))}
        </div>

        <div className="field">
          <label>Outcomes</label>
          <textarea
            placeholder="Key outcomes or agreements..."
            value={form.outcomes}
            onChange={handleChange("outcomes")}
          />
        </div>

        <div className="field" style={{ marginTop: 14 }}>
          <label>Follow-up Actions</label>
          <textarea
            placeholder="Enter next steps or tasks..."
            value={form.follow_up_actions}
            onChange={handleChange("follow_up_actions")}
          />
        </div>

        {suggestedFollowups.length > 0 && (
          <div className="followups">
            AI Suggested Follow-ups:
            <ul>
              {suggestedFollowups.map((f, i) => (
                <li key={i}>{f}</li>
              ))}
            </ul>
          </div>
        )}

        <button className="submit-btn" type="submit" disabled={submitStatus === "loading"}>
          {submitStatus === "loading" ? "Logging..." : "Log Interaction"}
        </button>

        {submitStatus === "succeeded" && (
          <div className="status-msg success">Interaction logged successfully.</div>
        )}
        {submitStatus === "failed" && (
          <div className="status-msg error">Something went wrong. Please try again.</div>
        )}
      </form>
    </div>
  );
}
