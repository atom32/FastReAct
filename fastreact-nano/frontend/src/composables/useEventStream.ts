/**
 * Event stream composable
 */

import { ref } from "vue";
import { useEventsStore } from "../stores/events";
import { useSessionStore } from "../stores/session";
import type { WebSocketClient } from "../services/websocket";
import type { WebSocketMessage, AgentEvent } from "../types/events";

export function useEventStream(wsClient: WebSocketClient) {
  const eventsStore = useEventsStore();
  const sessionStore = useSessionStore();

  const isProcessing = ref(false);

  // Process incoming WebSocket messages
  function processMessage(message: WebSocketMessage) {
    if (!message.data) return;

    const event = message.data as AgentEvent;
    processEvent(event, message.session_id);
  }

  // Process individual AgentEvent
  function processEvent(event: AgentEvent, sessionId?: string) {
    isProcessing.value = true;

    switch (event.type) {
      case "session_start":
        eventsStore.setStreaming(true);
        eventsStore.clearCurrentSession();

        if (event.session_id) {
          sessionStore.setCurrentSession(event.session_id);
          sessionStore.addSession({
            session_id: event.session_id,
            created_at: event.timestamp,
            last_active: event.timestamp,
            status: "active",
            event_count: 0,
            config: event.config,
          });
        }
        break;

      case "session_end":
        eventsStore.setStreaming(false);

        if (event.session_id) {
          sessionStore.updateSessionStatus(event.session_id, "idle");
        }
        break;

      case "think":
        // Thinking is accumulated in currentThinking
        break;

      case "tool_call":
      case "tool_result":
      case "error":
      case "message":
        // All other events are added to the buffer
        eventsStore.addEvent(event, sessionId);
        break;

      default:
        console.warn("Unknown event type:", (event as any).type);
    }

    isProcessing.value = false;
  }

  // Subscribe to WebSocket messages
  function subscribe() {
    wsClient.onMessage(processMessage);
  }

  // Unsubscribe from WebSocket messages
  function unsubscribe() {
    // WebSocket client handles cleanup
  }

  // Send query via WebSocket
  function sendQuery(content: string) {
    const sessionId = sessionStore.currentSessionId;
    wsClient.sendQuery(content, sessionId || undefined);
  }

  return {
    // State
    isProcessing,

    // Computed from stores
    events: eventsStore.currentSessionEvents,
    isStreaming: eventsStore.isStreaming,
    currentThinking: eventsStore.currentThinking,

    // Actions
    processMessage,
    processEvent,
    subscribe,
    unsubscribe,
    sendQuery,
  };
}
