"use client";

import { motion } from "framer-motion";
import type { AeonState, Emotion } from "../lib/zana-stream";

interface Props {
  state: AeonState;
  emotion?: Emotion;
  surprise?: number;
}

const STATE_CONFIG: Record<AeonState, { color: string; glow: string; label: string; pulseScale: number[] }> = {
  idle:      { color: "#3B82F6", glow: "rgba(59,130,246,0.4)",   label: "EN REPOSO",    pulseScale: [1, 1.04, 1] },
  listening: { color: "#FFD700", glow: "rgba(255,215,0,0.5)",    label: "ESCUCHANDO",   pulseScale: [1, 1.12, 1] },
  thinking:  { color: "#A855F7", glow: "rgba(168,85,247,0.5)",   label: "PROCESANDO",   pulseScale: [1, 1.08, 1] },
  speaking:  { color: "#4ADE80", glow: "rgba(74,222,128,0.5)",   label: "RESPONDIENDO", pulseScale: [1, 1.15, 1] },
};

const EMOTION_RING: Record<Emotion, string> = {
  neutral:   "rgba(255,255,255,0.15)",
  joy:       "rgba(59,130,246,0.4)",
  surprise:  "rgba(255,215,0,0.5)",
  fear:      "rgba(100,116,139,0.4)",
  anger:     "rgba(239,68,68,0.5)",
  sadness:   "rgba(59,130,246,0.2)",
  curiosity: "rgba(168,85,247,0.4)",
  trust:     "rgba(74,222,128,0.4)",
};

export default function AeonFace({ state, emotion = "neutral", surprise }: Props) {
  const cfg = STATE_CONFIG[state];
  const ringColor = EMOTION_RING[emotion];

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="relative w-52 h-52 flex items-center justify-center">
        {/* outer glow */}
        <motion.div
          animate={{ scale: cfg.pulseScale, opacity: [0.3, 0.6, 0.3] }}
          transition={{ duration: state === "speaking" ? 1 : 2.5, repeat: Infinity, ease: "easeInOut" }}
          className="absolute inset-0 rounded-full blur-[50px]"
          style={{ backgroundColor: cfg.glow }}
        />

        {/* emotion ring */}
        <motion.div
          animate={{ rotate: state === "thinking" ? 360 : 0 }}
          transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
          className="absolute inset-2 rounded-full border-2"
          style={{ borderColor: ringColor }}
        />

        {/* core sphere */}
        <motion.div
          animate={{ scale: cfg.pulseScale }}
          transition={{ duration: state === "listening" ? 0.6 : 1.8, repeat: Infinity, ease: "easeInOut" }}
          className="absolute inset-6 rounded-full"
          style={{
            background: `radial-gradient(circle at 38% 35%, ${cfg.color}cc, ${cfg.color}44)`,
            boxShadow: `0 0 40px ${cfg.glow}, inset 0 0 20px rgba(255,255,255,0.05)`,
          }}
        />

        {/* ZANA eye */}
        <div
          className="relative z-10 w-8 h-8 rounded-full border-2"
          style={{ backgroundColor: `${cfg.color}33`, borderColor: cfg.color, boxShadow: `0 0 12px ${cfg.glow}` }}
        />

        {/* surprise burst */}
        {surprise !== undefined && surprise > 0.4 && (
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1.3, opacity: 0 }}
            transition={{ duration: 0.8, repeat: Infinity }}
            className="absolute inset-0 rounded-full border"
            style={{ borderColor: cfg.color }}
          />
        )}
      </div>

      {/* state label */}
      <div className="flex flex-col items-center gap-1">
        <span
          className="text-xs font-bold tracking-[0.2em] uppercase"
          style={{ color: cfg.color }}
        >
          {cfg.label}
        </span>
        {surprise !== undefined && (
          <span className="text-[10px] font-mono text-slate-500">
            S: {surprise.toFixed(3)}
          </span>
        )}
      </div>
    </div>
  );
}
