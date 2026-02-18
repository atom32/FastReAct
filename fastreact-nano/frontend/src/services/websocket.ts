/**
 * WebSocket client for Gateway communication
 */

import { ref, computed } from "vue";
import type { Ref } from "vue";
import type { WebSocketMessage } from "../types/events";

export type WebSocketStatus = "connecting" | "connected" | "disconnected" | "error";

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private reconnectTimer: number | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000; // Start with 1 second

  public status: Ref<WebSocketStatus> = ref("disconnected");
  public messageHandlers: Array<(message: WebSocketMessage) => void> = [];
  public errorHandler: ((error: Event) => void) | null = null;

  constructor(private url: string) {}

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log("[WebSocket] Already connected");
      return;
    }

    this.status.value = "connecting";
    console.log(`[WebSocket] Connecting to ${this.url}`);

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log("[WebSocket] Connected");
        this.status.value = "connected";
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;

        if (this.reconnectTimer) {
          clearTimeout(this.reconnectTimer);
          this.reconnectTimer = null;
        }
      };

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          this.messageHandlers.forEach((handler) => handler(message));
        } catch (error) {
          console.error("[WebSocket] Failed to parse message:", error);
        }
      };

      this.ws.onerror = (error) => {
        console.error("[WebSocket] Error:", error);
        this.status.value = "error";
        if (this.errorHandler) {
          this.errorHandler(error);
        }
      };

      this.ws.onclose = () => {
        console.log("[WebSocket] Connection closed");
        this.status.value = "disconnected";
        this.scheduleReconnect();
      };
    } catch (error) {
      console.error("[WebSocket] Failed to create connection:", error);
      this.status.value = "error";
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error("[WebSocket] Max reconnect attempts reached");
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1); // Exponential backoff

    console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

    this.reconnectTimer = window.setTimeout(() => {
      this.connect();
    }, delay);
  }

  sendQuery(content: string, sessionId?: string): void {
    if (this.ws?.readyState !== WebSocket.OPEN) {
      throw new Error("WebSocket is not connected");
    }

    const message: WebSocketMessage = {
      type: "query",
      query: content,
      session_id: sessionId,
    };

    this.ws.send(JSON.stringify(message));
    console.log("[WebSocket] Sent query:", content.substring(0, 50) + "...");
  }

  onMessage(handler: (message: WebSocketMessage) => void): () => void {
    this.messageHandlers.push(handler);

    // Return unsubscribe function
    return () => {
      const index = this.messageHandlers.indexOf(handler);
      if (index > -1) {
        this.messageHandlers.splice(index, 1);
      }
    };
  }

  onError(handler: (error: Event) => void): void {
    this.errorHandler = handler;
  }

  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.status.value = "disconnected";
    this.reconnectAttempts = 0;
  }

  isConnected(): boolean {
    return this.status.value === "connected" && this.ws?.readyState === WebSocket.OPEN;
  }
}

// Global WebSocket client instance
let globalWSClient: WebSocketClient | null = null;

export function useWebSocket(url: string = "ws://localhost:9000/ws") {
  if (!globalWSClient) {
    globalWSClient = new WebSocketClient(url);
  }

  return {
    client: globalWSClient,
    status: computed(() => globalWSClient!.status.value),
    connect: () => globalWSClient!.connect(),
    disconnect: () => globalWSClient!.disconnect(),
  };
}
