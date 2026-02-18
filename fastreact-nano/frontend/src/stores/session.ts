/**
 * Session state management
 */

import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { APISession } from "../types/api";

export const useSessionStore = defineStore("session", () => {
  // State
  const sessions = ref<APISession[]>([]);
  const currentSessionId = ref<string | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  // Computed
  const activeSessions = computed(() =>
    sessions.value.filter((s) => s.status === "active")
  );

  const currentSession = computed(() =>
    sessions.value.find((s) => s.session_id === currentSessionId.value)
  );

  const sessionCount = computed(() => sessions.value.length);

  // Actions
  async function fetchSessions() {
    loading.value = true;
    error.value = null;

    try {
      // Will be implemented with API client
      // const api = useAPI();
      // sessions.value = await api.listSessions();
      sessions.value = [];
    } catch (e: any) {
      error.value = e.message;
      console.error("Failed to fetch sessions:", e);
    } finally {
      loading.value = false;
    }
  }

  function setCurrentSession(sessionId: string | null) {
    currentSessionId.value = sessionId;
  }

  function addSession(session: APISession) {
    const index = sessions.value.findIndex(
      (s) => s.session_id === session.session_id
    );

    if (index > -1) {
      sessions.value[index] = session;
    } else {
      sessions.value.push(session);
    }
  }

  function removeSession(sessionId: string) {
    const index = sessions.value.findIndex(
      (s) => s.session_id === sessionId
    );

    if (index > -1) {
      sessions.value.splice(index, 1);
    }

    if (currentSessionId.value === sessionId) {
      currentSessionId.value = null;
    }
  }

  function updateSessionStatus(
    sessionId: string,
    status: APISession["status"]
  ) {
    const session = sessions.value.find((s) => s.session_id === sessionId);

    if (session) {
      session.status = status;
    }
  }

  function clearSessions() {
    sessions.value = [];
    currentSessionId.value = null;
  }

  return {
    // State
    sessions,
    currentSessionId,
    loading,
    error,

    // Computed
    activeSessions,
    currentSession,
    sessionCount,

    // Actions
    fetchSessions,
    setCurrentSession,
    addSession,
    removeSession,
    updateSessionStatus,
    clearSessions,
  };
});
