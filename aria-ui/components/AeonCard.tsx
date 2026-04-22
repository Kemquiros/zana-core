"use client";

import { useRef, useState, useCallback } from "react";
import { motion, useMotionValue, useTransform, useSpring } from "framer-motion";

export interface AeonDef {
  id: string;
  name: string;
  role: string;
  description: string;
  model: string;
  costTier: "low" | "mid" | "high";
  latency: "fast" | "medium" | "slow";
  tools: string[];
  gradient: string;        // Tailwind gradient classes
  glowColor: string;       // CSS color for box-shadow
  borderColor: string;     // CSS border color
  icon: string;            // emoji or text icon
  accentColor: string;     // hex for text accent
}

export const AEONS: AeonDef[] = [
  {
    id: "sentinel",
    name: "Sentinel",
    role: "Security & Anomaly Guard",
    description: "Watches every input and output. PII detection, injection patterns, threat classification. First and last line of defense.",
    model: "claude-haiku",
    costTier: "low",
    latency: "fast",
    tools: ["armor_scan", "threat_classify", "audit_log"],
    gradient: "from-red-950 via-rose-900 to-black",
    glowColor: "rgba(239,68,68,0.4)",
    borderColor: "rgba(239,68,68,0.3)",
    icon: "⚔️",
    accentColor: "#f87171",
  },
  {
    id: "archivist",
    name: "Archivist",
    role: "Memory & Knowledge Retrieval",
    description: "Semantic search across your entire vault. Retrieves context from ChromaDB. The memory of the empire.",
    model: "claude-haiku",
    costTier: "low",
    latency: "fast",
    tools: ["semantic_search", "memory_recall", "vault_embed"],
    gradient: "from-amber-950 via-yellow-900 to-black",
    glowColor: "rgba(245,158,11,0.4)",
    borderColor: "rgba(245,158,11,0.3)",
    icon: "📚",
    accentColor: "#fbbf24",
  },
  {
    id: "analyst",
    name: "Analyst",
    role: "Data Reasoning & Inference",
    description: "Forward-chaining over structured facts. Triggers the Rust reasoning engine. Produces traceable deductions with confidence scores.",
    model: "claude-sonnet",
    costTier: "mid",
    latency: "medium",
    tools: ["reason", "symbolic_infer", "data_analyze"],
    gradient: "from-blue-950 via-cyan-900 to-black",
    glowColor: "rgba(59,130,246,0.4)",
    borderColor: "rgba(59,130,246,0.3)",
    icon: "📊",
    accentColor: "#60a5fa",
  },
  {
    id: "operator",
    name: "Operator",
    role: "Execution & External Actions",
    description: "Runs code, calls APIs, fires webhooks. Translates cognitive decisions into real-world effects. Action without hallucination.",
    model: "claude-sonnet",
    costTier: "mid",
    latency: "medium",
    tools: ["bash", "http_call", "file_edit", "git"],
    gradient: "from-emerald-950 via-green-900 to-black",
    glowColor: "rgba(16,185,129,0.4)",
    borderColor: "rgba(16,185,129,0.3)",
    icon: "⚙️",
    accentColor: "#34d399",
  },
  {
    id: "herald",
    name: "Herald",
    role: "Communication & Reporting",
    description: "Drafts messages, posts to Slack/Discord/Telegram, generates reports. The voice of the empire to the outside world.",
    model: "claude-haiku",
    costTier: "low",
    latency: "fast",
    tools: ["slack_send", "discord_send", "telegram_send", "draft"],
    gradient: "from-violet-950 via-purple-900 to-black",
    glowColor: "rgba(139,92,246,0.4)",
    borderColor: "rgba(139,92,246,0.3)",
    icon: "📣",
    accentColor: "#a78bfa",
  },
  {
    id: "forge",
    name: "Forge",
    role: "Code Generation & Architecture",
    description: "Full-stack engineering at scale. Writes, tests, refactors, deploys. Remembers your architecture decisions across sessions.",
    model: "claude-opus",
    costTier: "high",
    latency: "slow",
    tools: ["code_gen", "test_runner", "architecture", "refactor"],
    gradient: "from-orange-950 via-red-900 to-black",
    glowColor: "rgba(249,115,22,0.4)",
    borderColor: "rgba(249,115,22,0.3)",
    icon: "🔨",
    accentColor: "#fb923c",
  },
  {
    id: "scholar",
    name: "Scholar",
    role: "Research & Long-form Synthesis",
    description: "Reads papers, synthesizes knowledge, builds structured mental models. Your research partner with persistent episodic memory.",
    model: "claude-opus",
    costTier: "high",
    latency: "slow",
    tools: ["pdf_read", "web_search", "synthesis", "cite"],
    gradient: "from-indigo-950 via-blue-900 to-black",
    glowColor: "rgba(99,102,241,0.4)",
    borderColor: "rgba(99,102,241,0.3)",
    icon: "🎓",
    accentColor: "#818cf8",
  },
  {
    id: "watcher",
    name: "Watcher",
    role: "Vision & Multimodal Monitoring",
    description: "Analyzes images, video frames, screenshots. Identifies scenes, entities, anomalies. Sees what text cannot describe.",
    model: "claude-sonnet",
    costTier: "mid",
    latency: "medium",
    tools: ["vision_analyze", "ocr", "scene_classify", "entity_detect"],
    gradient: "from-slate-900 via-zinc-800 to-black",
    glowColor: "rgba(148,163,184,0.4)",
    borderColor: "rgba(148,163,184,0.3)",
    icon: "👁️",
    accentColor: "#94a3b8",
  },
];

const COST_LABEL = { low: "🟢 Low cost", mid: "🟡 Mid cost", high: "🔴 Premium" };
const LATENCY_LABEL = { fast: "⚡ Fast", medium: "◎ Balanced", slow: "◉ Deep" };

interface AeonCardProps {
  aeon: AeonDef;
  active?: boolean;
  onClick?: (id: string) => void;
}

export default function AeonCard({ aeon, active = false, onClick }: AeonCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [isHovered, setIsHovered] = useState(false);

  // Mouse-tracked perspective values
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  const springConfig = { damping: 20, stiffness: 200 };
  const rotateX = useSpring(useTransform(mouseY, [-0.5, 0.5], [8, -8]), springConfig);
  const rotateY = useSpring(useTransform(mouseX, [-0.5, 0.5], [-10, 10]), springConfig);

  // Sheen highlight position
  const sheenX = useTransform(mouseX, [-0.5, 0.5], ["0%", "100%"]);
  const sheenY = useTransform(mouseY, [-0.5, 0.5], ["0%", "100%"]);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width - 0.5;
    const y = (e.clientY - rect.top) / rect.height - 0.5;
    mouseX.set(x);
    mouseY.set(y);
  }, [mouseX, mouseY]);

  const handleMouseLeave = useCallback(() => {
    mouseX.set(0);
    mouseY.set(0);
    setIsHovered(false);
  }, [mouseX, mouseY]);

  return (
    <div style={{ perspective: "1200px" }} className="w-full">
      <motion.div
        ref={cardRef}
        className="relative w-full cursor-pointer select-none overflow-hidden rounded-[2rem]"
        style={{
          rotateX,
          rotateY,
          transformStyle: "preserve-3d",
          boxShadow: isHovered
            ? `0 30px 80px ${aeon.glowColor}, 0 0 0 2px ${aeon.borderColor}, inset 0 1px 0 rgba(255,255,255,0.2)`
            : `0 8px 30px rgba(0,0,0,0.8), 0 0 0 1px rgba(255,255,255,0.05)`,
        }}
        animate={{
          scale: isHovered ? 1.05 : active ? 1.03 : 1,
          z: isHovered ? 60 : 0,
        }}
        transition={{ duration: 0.3, ease: [0.23, 1, 0.32, 1] }}
        onMouseMove={handleMouseMove}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={handleMouseLeave}
        onClick={() => onClick?.(aeon.id)}
      >
        {/* Background layer */}
        <div className={`absolute inset-0 bg-gradient-to-br ${aeon.gradient} opacity-95`} />

        {/* Ambient occlusion glow */}
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.1),transparent)] pointer-events-none" />

        {/* Floating Icon with Depth */}
        <div className="relative z-20 p-7 flex flex-col h-full gap-4">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-4">
              <motion.div
                className="text-5xl drop-shadow-[0_10px_10px_rgba(0,0,0,0.5)]"
                style={{ transform: "translateZ(50px)" }}
                animate={isHovered ? { 
                  y: [-4, 4, -4],
                  rotate: [0, -5, 5, 0],
                  scale: 1.1
                } : { y: 0 }}
                transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
              >
                {aeon.icon}
              </motion.div>
              <div style={{ transform: "translateZ(30px)" }}>
                <h3
                  className="font-black text-xl tracking-tighter uppercase italic"
                  style={{ color: aeon.accentColor }}
                >
                  {aeon.name}
                </h3>
                <p className="text-[10px] font-mono text-white/40 uppercase tracking-widest">{aeon.role}</p>
              </div>
            </div>
          </div>

          <div style={{ transform: "translateZ(20px)" }} className="flex-1">
            <p className="text-xs text-white/70 leading-relaxed font-medium">
              {aeon.description}
            </p>
          </div>

          {/* Bottom stats */}
          <div style={{ transform: "translateZ(15px)" }} className="flex items-center justify-between pt-4 border-t border-white/10">
            <div className="flex flex-wrap gap-1.5">
              {aeon.tools.slice(0, 2).map(t => (
                <span key={t} className="text-[8px] font-mono px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-white/40 uppercase">
                  {t}
                </span>
              ))}
            </div>
            <div className="text-right">
                <p className="text-[9px] font-mono text-white/30 uppercase tracking-tighter">{aeon.model}</p>
                <p className="text-[9px] font-bold text-white/60 uppercase">{LATENCY_LABEL[aeon.latency].split(' ')[1]}</p>
            </div>
          </div>
        </div>

        {/* Glass sheen */}
        <div className="absolute inset-0 pointer-events-none opacity-20 bg-[linear-gradient(110deg,transparent,rgba(255,255,255,0.1)_45%,rgba(255,255,255,0.2)_50%,rgba(255,255,255,0.1)_55%,transparent)]" />
      </motion.div>
    </div>
  );
}
