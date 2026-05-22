"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { getGatewayStatus } from "./tauri-bridge";

// ─── SPROUT mode helpers ───────────────────────────────────────────────────────

async function checkSproutAvailable(): Promise<boolean> {
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: [] }),
    });
    return res.status !== 503;
  } catch {
    return false;
  }
}

interface SproutChunkPayload {
  delta?: string;
  error?: string;
}

async function fetchSproutStream(
  messages: Array<{ role: string; content: string }>,
  onChunk: (delta: string) => void,
  onDone: () => void,
  onError: (msg: string) => void,
): Promise<void> {
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages }),
    });

    if (!res.ok || !res.body) {
      onError(`HTTP ${res.status}`);
      onDone();
      return;
    }

    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let buf = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const lines = buf.split("\n");
      buf = lines.pop() ?? "";
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const payload = line.slice(6).trim();
        if (payload === "[DONE]") {
          onDone();
          return;
        }
        try {
          const parsed = JSON.parse(payload) as SproutChunkPayload;
          if (parsed.error) {
            onError(parsed.error);
          } else if (parsed.delta) {
            onChunk(parsed.delta);
          }
        } catch {
          /* skip malformed lines */
        }
      }
    }
    onDone();
  } catch (err) {
    onError(err instanceof Error ? err.message : "sprout_stream_error");
    onDone();
  }
}

export type AeonState = "idle" | "listening" | "thinking" | "speaking";
export type Modality = "text" | "audio" | "vision";
export type Emotion = "joy" | "surprise" | "fear" | "anger" | "sadness" | "neutral" | "curiosity" | "trust";

export interface Message {
  id: string;
  role: "user" | "aeon" | "system";
  text: string;
  modality?: Modality;
  emotion?: Emotion;
  surprise?: number;
  audioB64?: string;
  timestamp: number;
}

interface PerceptionEvent {
  text?: string;
  response_text?: string;
  response_emotion?: Emotion;
  kalman_surprise?: number;
  response_audio_b64?: string;
  modality?: Modality;
}

const wsUrl = (httpUrl?: string) => {
  if (httpUrl) return httpUrl.replace("http://", "ws://").replace("https://", "wss://") + "/sense/stream";

  if (typeof window !== "undefined") {
    const envUrl = process.env.NEXT_PUBLIC_GATEWAY_URL;
    if (envUrl && envUrl.startsWith("http")) {
      return envUrl.replace("http://", "ws://").replace("https://", "wss://") + "/sense/stream";
    }
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${window.location.host}/sense/stream`;
  }

  return "ws://localhost:54446/sense/stream";
};

export function useZanaStream(sessionId: string) {
  const [connected, setConnected] = useState(false);
  const [sproutMode, setSproutMode] = useState(false);
  const [aeonState, setAeonState] = useState<AeonState>("idle");
  const [messages, setMessages] = useState<Message[]>([]);
  const [audioLevel, setAudioLevel] = useState(0);

  const ws = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<NodeJS.Timeout | null>(null);
  // Conversation history for SPROUT mode (role/content pairs for LLM context)
  const sproutHistory = useRef<Array<{ role: string; content: string }>>([]);

  const addMessage = useCallback((msg: Omit<Message, "id" | "timestamp">) => {
    setMessages((prev) => [
      ...prev,
      { ...msg, id: crypto.randomUUID(), timestamp: Date.now() },
    ]);
  }, []);

  const connectRef = useRef<() => void>(undefined);

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
      // Check if SPROUT mode is available before scheduling reconnect
      checkSproutAvailable().then((available) => {
        setSproutMode(available);
        if (available) {
          addMessage({
            role: "system",
            text: "◈ MODO SPROUT activo — Gateway offline. LLM directo disponible.",
          });
        }
      });
      reconnectTimer.current = setTimeout(() => {
        if (connectRef.current) connectRef.current();
      }, 3000);
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
    connectRef.current = connect;
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
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

  const sendTextSprout = useCallback(
    (text: string) => {
      if (!text.trim()) return;

      // Add user message to UI and history
      addMessage({ role: "user", text, modality: "text" });
      sproutHistory.current.push({ role: "user", content: text });
      setAeonState("thinking");

      // Placeholder message id for streaming into
      const aeonMsgId = crypto.randomUUID();
      const timestamp = Date.now();
      setMessages((prev) => [
        ...prev,
        { id: aeonMsgId, role: "aeon", text: "", timestamp },
      ]);

      let accumulated = "";

      fetchSproutStream(
        [...sproutHistory.current],
        (delta) => {
          accumulated += delta;
          setMessages((prev) =>
            prev.map((m) => (m.id === aeonMsgId ? { ...m, text: accumulated } : m)),
          );
        },
        () => {
          setAeonState("idle");
          if (accumulated) {
            sproutHistory.current.push({ role: "assistant", content: accumulated });
          }
        },
        (errMsg) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === aeonMsgId ? { ...m, text: `[Error SPROUT: ${errMsg}]` } : m,
            ),
          );
          setAeonState("idle");
        },
      );
    },
    [addMessage],
  );

  useEffect(() => {
    if (aeonState === "speaking" || aeonState === "listening") {
      const interval = setInterval(() => setAudioLevel(Math.random()), 100);
      return () => clearInterval(interval);
    } else {
      setAudioLevel(0);
    }
  }, [aeonState]);

  return {
    connected,
    sproutMode,
    aeonState,
    setAeonState,
    messages,
    sendText,
    sendTextSprout,
    sendAudio,
    sendImage,
    audioLevel,
    connect,
  };
}
