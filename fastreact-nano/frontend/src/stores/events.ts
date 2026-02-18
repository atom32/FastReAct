/**
 * Event buffer state management
 */

import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { AgentEvent } from "../types/events";

export const useEventsStore = defineStore("events", () => {
  // State
  const events = ref<Map<string, AgentEvent[]>>(new Map());
  const currentSessionEvents = ref<AgentEvent[]>([]);
  const currentThinking = ref<string>("");
  const isStreaming = ref(false);

  // Computed
  const eventCount = computed(() => currentSessionEvents.value.length);

  const toolCalls = computed(() =>
    currentSessionEvents.value.filter((e) => e.type === "tool_call")
  );

  const errors = computed(() =>
    currentSessionEvents.value.filter((e) => e.type === "error")
  );

  const messages = computed(() =>
    currentSessionEvents.value.filter((e) => e.type === "message")
  );

  // Actions
  function addEvent(event: AgentEvent, sessionId?: string) {
    currentSessionEvents.value.push(event);

    if (sessionId) {
      if (!events.value.has(sessionId)) {
        events.value.set(sessionId, []);
      }
      events.value.get(sessionId)!.push(event);
    }

    // Handle special event types
    if (event.type === "think") {
      currentThinking.value += event.content || "";
    } else if (event.type === "session_end") {
      isStreaming.value = false;
    }
  }

  function clearCurrentSession() {
    currentSessionEvents.value = [];
    currentThinking.value = "";
    isStreaming.value = false;
  }

  function setStreaming(streaming: boolean) {
    isStreaming.value = streaming;
  }

  function getEventsForSession(sessionId: string): AgentEvent[] {
    return events.value.get(sessionId) || [];
  }

  function clearAllEvents() {
    events.value.clear();
    clearCurrentSession();
  }

  function removeSession(sessionId: string) {
    events.value.delete(sessionId);
  }

  return {
    // State
    events,
    currentSessionEvents,
    currentThinking,
    isStreaming,

    // Computed
    eventCount,
    toolCalls,
    errors,
    messages,

    // Actions
    addEvent,
    clearCurrentSession,
    setStreaming,
    getEventsForSession,
    clearAllEvents,
    removeSession,
  };
});
