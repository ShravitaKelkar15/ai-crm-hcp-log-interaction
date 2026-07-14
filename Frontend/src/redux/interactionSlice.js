import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import axios from "axios";

const API_BASE = "/api";

export const submitInteraction = createAsyncThunk(
  "interaction/submit",
  async (formData) => {
    const res = await axios.post(`${API_BASE}/interactions`, formData);
    return res.data;
  }
);

export const sendChatMessage = createAsyncThunk(
  "interaction/sendChatMessage",
  async ({ message, sessionId }) => {
    const res = await axios.post(`${API_BASE}/chat`, {
      message,
      session_id: sessionId,
    });
    return { message, ...res.data };
  }
);

const initialFormState = {
  hcp_name: "",
  interaction_type: "Meeting",
  interaction_date: new Date().toISOString().slice(0, 16),
  attendees: [],
  topics_discussed: "",
  materials_shared: [],
  samples_distributed: [],
  sentiment: "Neutral",
  outcomes: "",
  follow_up_actions: "",
};

const interactionSlice = createSlice({
  name: "interaction",
  initialState: {
    form: initialFormState,
    chatMessages: [],
    suggestedFollowups: [
      "Schedule follow-up meeting in 2 weeks",
      "Send OncoBoost Phase III PDF",
      "Add HCP to advisory board invite list",
    ],
    submitStatus: "idle",
    chatStatus: "idle",
    error: null,
  },
  reducers: {
    updateField(state, action) {
      const { field, value } = action.payload;
      state.form[field] = value;
    },
    resetForm(state) {
      state.form = initialFormState;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(submitInteraction.pending, (state) => {
        state.submitStatus = "loading";
      })
      .addCase(submitInteraction.fulfilled, (state) => {
        state.submitStatus = "succeeded";
        state.form = initialFormState;
      })
      .addCase(submitInteraction.rejected, (state, action) => {
        state.submitStatus = "failed";
        state.error = action.error.message;
      })
      .addCase(sendChatMessage.pending, (state, action) => {
        state.chatStatus = "loading";
        state.chatMessages.push({ role: "user", text: action.meta.arg.message });
      })
      .addCase(sendChatMessage.fulfilled, (state, action) => {
        state.chatStatus = "succeeded";
        state.chatMessages.push({ role: "assistant", text: action.payload.reply });
      })
      .addCase(sendChatMessage.rejected, (state, action) => {
        state.chatStatus = "failed";
        state.error = action.error.message;
        state.chatMessages.push({
          role: "assistant",
          text: "Sorry, something went wrong logging that.",
        });
      });
  },
});

export const { updateField, resetForm } = interactionSlice.actions;
export default interactionSlice.reducer;
