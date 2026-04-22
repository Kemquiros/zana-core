"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { getGatewayStatus } from "./tauri-bridge";

export type AeonState = "idle" | "listening" | "thinking" | "speaking";
export type Emotion = "neutral" | "calm" | "excited" | "agitated" | "subdued";

export interface PerceptionEvent {
  modality: "text" | "audio" | "vision" | "multimodal";
  text?: string;
  response_text?: string;
  response_audio_b64?: string;
  response_emotion?: Emotion;
  kalman_surprise?: number;
  session_id?: string;
}

export interface Message {
  id: string;
  role: "user" | "aeon" | "system";
  text: string;
  emotion?: Emotion;
  surprise?: number;
  audioB64?: string;
  timestamp: number;
  modality?: string;
}

// NEXT_PUBLIC_GATEWAY_URL must be set in .env.local for dev
// or injected by Docker/Caddy for production.
const GATEWAY_URL =
  process.env.NEXT_PUBLIC_GATEWAY_URL ?? "http://localhost:54446";

function wsUrl(override?: string) {
  const base = override ?? GATEWAY_URL;
  return `${base.replace(/^http/, "ws")}/sense/stream`;
}

export function useZanaStream(sessionId: string) {
  const ws = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [aeonState, setAeonState] = useState<AeonState>("idle");
  const [messages, setMessages] = useState<Message[]>([]);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const addMessage = useCallback((msg: Omit<Message, "id" | "timestamp">) => {
    setMessages((prev) => [
      ...prev,
      { ...msg, id: crypto.randomUUID(), timestamp: Date.now() },
    ]);
  }, []);

  const connect = useCallback(async () => {
    if (ws.current?.readyState === WebSocket.OPEN) return;

    // In Tauri, ask the Rust backend for the live gateway URL
    const tauriStatus = await getGatewayStatus();
    const url = wsUrl(tauriStatus?.url);
    const socket = new WebSocket(url);
    ws.current = socket;

    socket.onopen = () => {
      setConnected(true);
      setAeonState("idle");
      addMessage({ role: "system", text: "ZANA conectado. Habla, escribe o comparte una imagen." });
    };

    socket.onclose = () => {
      setConnected(false);
      setAeonState("idle");
      reconnectTimer.current = setTimeout(() => { connect(); }, 3000);
    };

    socket.onerror = () => {
      socket.close();
    };

    socket.onmessage = (evt) => {
      try {
        const event: PerceptionEvent = JSON.parse(evt.data);
        setAeonState("idle");
        addMessage({
          role: "aeon",
          text: event.response_text ?? event.text ?? "",
          emotion: event.response_emotion,
          surprise: event.kalman_surprise,
          audioB64: event.response_audio_b64,
          modality: event.modality,
        });
      } catch {
        /* malformed frame — ignore */
      }
    };
  }, [addMessage]);

  useEffect(() => {
    connect();
    return () => {
      reconnectTimer.current && clearTimeout(reconnectTimer.current);
      ws.current?.close();
    };
  }, [connect]);

  const sendText = useCallback(
    (text: string) => {
      if (!ws.current || ws.current.readyState !== WebSocket.OPEN) return;
      addMessage({ role: "user", text, modality: "text" });
      setAeonState("thinking");
      ws.current.send(JSON.stringify({ type: "text", data: text, session_id: sessionId }));
    },
    [addMessage, sessionId],
  );

  const sendAudio = useCallback(
    (wavB64: string) => {
      if (!ws.current || ws.current.readyState !== WebSocket.OPEN) return;
      addMessage({ role: "user", text: "🎤 Audio enviado", modality: "audio" });
      setAeonState("thinking");
      ws.current.send(JSON.stringify({ type: "audio", data: wavB64, session_id: sessionId }));
    },
    [addMessage, sessionId],
  );

  const sendImage = useCallback(
    (b64: string, mimeType: string) => {
      if (!ws.current || ws.current.readyState !== WebSocket.OPEN) return;
      addMessage({ role: "user", text: "🖼️ Imagen enviada", modality: "vision" });
      setAeonState("thinking");
      ws.current.send(
        JSON.stringify({ type: "vision", data: b64, mime: mimeType, session_id: sessionId }),
      );
    },
    [addMessage, sessionId],
  );

  return { connected, aeonState, setAeonState, messages, sendText, sendAudio, sendImage };
}
