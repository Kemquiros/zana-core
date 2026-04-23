"use client";

import { useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Mic, FileImage, Zap } from "lucide-react";
import type { Message, Emotion } from "../lib/zana-stream";

const EMOTION_COLOR: Record<Emotion, string> = {
  neutral:  "#94a3b8",
  calm:     "#3B82F6",
  excited:  "#FFD700",
  agitated: "#ef4444",
  subdued:  "#64748b",
};

function ModalityIcon({ modality }: { modality?: string }) {
  if (modality === "audio") return <Mic className="w-3 h-3" />;
  if (modality === "vision") return <FileImage className="w-3 h-3" />;
  return null;
}

function AudioPlayer({ b64 }: { b64: string }) {
  const play = useCallback(() => {
    const bytes = atob(b64);
    const arr = new Uint8Array(bytes.length);
    for (let i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i);
    const blob = new Blob([arr], { type: "audio/wav" });
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.onended = () => URL.revokeObjectURL(url);
    audio.play();
  }, [b64]);

  return (
    <button
      onClick={play}
      className="mt-2 px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest border border-white/10 text-slate-400 hover:text-white hover:border-white/30 transition-all flex items-center gap-1.5"
    >
      <Zap className="w-3 h-3" /> Reproducir voz
    </button>
  );
}

export default function ConversationFeed({ messages }: { messages: Message[] }) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto space-y-4 py-4 px-2 scrollbar-none">
      <AnimatePresence initial={false}>
        {messages.map((msg) => {
          const isUser = msg.role === "user";
          const isSystem = msg.role === "system";

          if (isSystem) {
            return (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex justify-center"
              >
                <span className="text-[10px] font-mono text-slate-600 px-3 py-1 rounded-full border border-white/5">
                  {msg.text}
                </span>
              </motion.div>
            );
          }

          return (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ duration: 0.25 }}
              className={`flex ${isUser ? "justify-end" : "justify-start"}`}
            >
              <div className={`max-w-[82%] ${isUser ? "items-end" : "items-start"} flex flex-col gap-1.5`}>
                {/* header */}
                <div className={`flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest ${isUser ? "flex-row-reverse" : ""}`}>
                  <span className={isUser ? "text-indigo-300" : "text-purple-400"}>
                    {isUser ? "TÚ" : "AEON"}
                  </span>
                  {msg.modality && (
                    <span className="text-gray-500 flex items-center gap-1">
                      <ModalityIcon modality={msg.modality} />
                    </span>
                  )}
                  {msg.emotion && msg.emotion !== "neutral" && (
                    <span
                      className="px-2 py-0.5 rounded-full text-[9px] bg-white/5 border border-white/10"
                      style={{ color: EMOTION_COLOR[msg.emotion] }}
                    >
                      {msg.emotion}
                    </span>
                  )}
                </div>

                {/* bubble */}
                <div
                  className={`px-4 py-3 rounded-2xl text-sm font-medium leading-relaxed shadow-lg ${
                    isUser
                      ? "bg-indigo-600/20 border border-indigo-500/30 text-white rounded-br-sm"
                      : "bg-white/5 border border-white/10 backdrop-blur-md text-gray-200 rounded-bl-sm"
                  }`}
                >
                  {msg.text}
                  {msg.surprise !== undefined && msg.surprise > 0.35 && (
                    <span className="ml-2 text-[10px] font-mono text-purple-400 opacity-80">
                      ⚡{msg.surprise.toFixed(2)}
                    </span>
                  )}
                </div>

                {msg.audioB64 && <AudioPlayer b64={msg.audioB64} />}
              </div>
            </motion.div>
          );
        })}
      </AnimatePresence>
      <div ref={bottomRef} />
    </div>
  );
}
