"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Brain, Clock, Zap, Search, RefreshCw, Activity, type LucideIcon } from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────────────────

interface GraphNode {
  id: string;
  type: string;
  label: string;
  weight: number;
  color: string;
  // computed during layout
  x?: number;
  y?: number;
}

interface GraphEdge {
  source: string;
  target: string;
  weight: number;
}

interface EpisodicRecord {
  session_id: string;
  role: "user" | "aeon";
  content: string;
  emotion?: string;
  kalman_surprise?: number;
  created_at: string;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  timeline: EpisodicRecord[];
  stats: {
    total_analysed: number;
    topics_extracted: number;
    edges: number;
    days_covered: number;
    dominant_emotion: string;
  };
}

// ── Constants ─────────────────────────────────────────────────────────────────

const EMOTION_COLORS: Record<string, string> = {
  joy:       "text-yellow-400 bg-yellow-400/10 border-yellow-400/30",
  curiosity: "text-cyan-400 bg-cyan-400/10 border-cyan-400/30",
  trust:     "text-emerald-400 bg-emerald-400/10 border-emerald-400/30",
  surprise:  "text-purple-400 bg-purple-400/10 border-purple-400/30",
  sadness:   "text-blue-400 bg-blue-400/10 border-blue-400/30",
  fear:      "text-orange-400 bg-orange-400/10 border-orange-400/30",
  anger:     "text-red-400 bg-red-400/10 border-red-400/30",
  neutral:   "text-gray-400 bg-gray-400/10 border-gray-400/30",
};

const SURPRISE_COLOR = (v: number) =>
  v > 2.0 ? "#ef4444" : v > 1.0 ? "#f59e0b" : "#6366f1";

// ── Layout: deterministic radial ──────────────────────────────────────────────

function computeLayout(nodes: GraphNode[], W: number, H: number): GraphNode[] {
  const cx = W / 2;
  const cy = H / 2;
  const sorted = [...nodes].sort((a, b) => b.weight - a.weight);

  const rings = [
    { count: 1,  r: 0 },
    { count: 5,  r: Math.min(W, H) * 0.18 },
    { count: 8,  r: Math.min(W, H) * 0.32 },
    { count: 999, r: Math.min(W, H) * 0.44 },
  ];

  let idx = 0;
  const result: GraphNode[] = [];

  for (const ring of rings) {
    const batch = sorted.slice(idx, idx + ring.count);
    if (batch.length === 0) break;
    batch.forEach((node, i) => {
      if (ring.r === 0) {
        result.push({ ...node, x: cx, y: cy });
      } else {
        const angle = (2 * Math.PI * i) / batch.length - Math.PI / 2;
        result.push({
          ...node,
          x: cx + ring.r * Math.cos(angle),
          y: cy + ring.r * Math.sin(angle),
        });
      }
    });
    idx += ring.count;
    if (idx >= sorted.length) break;
  }

  return result;
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function StatPill({ icon: Icon, label, value }: { icon: LucideIcon; label: string; value: string | number }) {
  return (
    <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 text-[10px] font-mono">
      <Icon size={12} className="text-indigo-400" />
      <span className="text-gray-500 uppercase tracking-wider">{label}</span>
      <span className="text-white font-bold">{value}</span>
    </div>
  );
}

function TimelineItem({ rec, active, onClick }: { rec: EpisodicRecord; active: boolean; onClick: () => void }) {
  const emotionClass = EMOTION_COLORS[rec.emotion ?? "neutral"] ?? EMOTION_COLORS.neutral;
  const surprise = rec.kalman_surprise ?? 0;

  return (
    <motion.button
      layout
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      onClick={onClick}
      className={`w-full text-left p-4 rounded-2xl border transition-all ${
        active
          ? "bg-indigo-500/10 border-indigo-500/40"
          : "bg-white/[0.02] border-white/5 hover:border-white/20"
      }`}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <span className={`text-[9px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full border ${emotionClass}`}>
          {rec.emotion ?? "neutral"}
        </span>
        <span className="text-[9px] text-gray-600 font-mono shrink-0">
          {new Date(rec.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </span>
      </div>
      <p className="text-xs text-gray-400 line-clamp-2 text-left leading-relaxed">
        {rec.content}
      </p>
      {/* Kalman surprise bar */}
      <div className="mt-2 h-0.5 w-full bg-white/5 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{
            width: `${Math.min(100, (surprise / 3) * 100)}%`,
            backgroundColor: SURPRISE_COLOR(surprise),
          }}
        />
      </div>
    </motion.button>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

export default function MemoryGraph() {
  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [query, setQuery] = useState("");
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const [activeRecord, setActiveRecord] = useState<EpisodicRecord | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [svgSize, setSvgSize] = useState({ w: 480, h: 400 });

  const fetchGraph = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const res = await fetch("/memory/graph?limit=150&top_topics=24");
      if (!res.ok) throw new Error("offline");
      const json: GraphData = await res.json();
      setData(json);
    } catch {
      // Show mock data so the UI renders even when the backend is offline
      setData(MOCK_DATA);
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchGraph(); }, [fetchGraph]);

  // Observe SVG container size
  useEffect(() => {
    if (!svgRef.current) return;
    const ro = new ResizeObserver((entries) => {
      const e = entries[0];
      if (e) setSvgSize({ w: e.contentRect.width, h: e.contentRect.height });
    });
    ro.observe(svgRef.current);
    return () => ro.disconnect();
  }, []);

  const laidOut = data ? computeLayout(data.nodes, svgSize.w, svgSize.h) : [];
  const nodeMap = Object.fromEntries(laidOut.map((n) => [n.id, n]));

  const filtered = data?.timeline.filter((r) =>
    query === "" ||
    r.content.toLowerCase().includes(query.toLowerCase()) ||
    (r.emotion ?? "").includes(query.toLowerCase())
  ) ?? [];

  // Which nodes are connected to the active node
  const connectedIds = activeNode
    ? new Set(
        data?.edges
          .filter((e) => e.source === activeNode || e.target === activeNode)
          .flatMap((e) => [e.source, e.target]) ?? []
      )
    : null;

  return (
    <section className="space-y-8">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <Brain size={18} className="text-indigo-400" />
            <h2 className="text-3xl font-black uppercase italic tracking-tighter">Memory Map</h2>
            {error && (
              <span className="text-[9px] font-mono text-yellow-500 uppercase tracking-widest px-2 py-0.5 rounded-full border border-yellow-500/30 bg-yellow-500/10">
                modo offline · datos demo
              </span>
            )}
          </div>
          <p className="text-gray-500 text-[11px] font-mono uppercase tracking-[0.3em]">
            grafo de conocimiento · extracción de tópicos episódicos
          </p>
        </div>
        <button
          onClick={fetchGraph}
          className="p-3 rounded-2xl bg-white/5 border border-white/10 text-gray-400 hover:text-white hover:bg-white/10 transition-all"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {/* Stats row */}
      {data && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-wrap gap-2"
        >
          <StatPill icon={Brain} label="Memorias" value={data.stats.total_analysed} />
          <StatPill icon={Activity} label="Tópicos" value={data.stats.topics_extracted} />
          <StatPill icon={Zap} label="Conexiones" value={data.stats.edges} />
          <StatPill icon={Clock} label="Días" value={data.stats.days_covered} />
          <StatPill icon={Activity} label="Emoción dom." value={data.stats.dominant_emotion} />
        </motion.div>
      )}

      {/* Main grid */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_400px] gap-6">

        {/* Graph panel */}
        <div className="relative rounded-[2rem] bg-white/[0.02] border border-white/10 overflow-hidden min-h-[420px]">
          {loading ? (
            <div className="absolute inset-0 flex items-center justify-center">
              <motion.div
                animate={{ scale: [1, 1.1, 1], opacity: [0.4, 0.8, 0.4] }}
                transition={{ duration: 2, repeat: Infinity }}
                className="w-16 h-16 rounded-full border-2 border-indigo-500/40 border-t-indigo-500"
              />
            </div>
          ) : (
            <svg
              ref={svgRef}
              className="w-full h-full min-h-[420px]"
              style={{ position: "absolute", inset: 0 }}
            >
              {/* Edges */}
              <g opacity={0.25}>
                {data?.edges.map((edge, i) => {
                  const s = nodeMap[edge.source];
                  const t = nodeMap[edge.target];
                  if (!s?.x || !t?.x) return null;
                  const isHighlighted =
                    activeNode === edge.source || activeNode === edge.target;
                  return (
                    <motion.line
                      key={i}
                      x1={s.x} y1={s.y} x2={t.x} y2={t.y}
                      stroke={isHighlighted ? "#6366f1" : "#ffffff"}
                      strokeWidth={isHighlighted ? edge.weight * 0.8 + 0.5 : 0.5}
                      opacity={isHighlighted ? 0.9 : 0.18}
                      initial={{ pathLength: 0, opacity: 0 }}
                      animate={{ pathLength: 1, opacity: isHighlighted ? 0.9 : 0.18 }}
                      transition={{ duration: 0.8, delay: i * 0.01 }}
                    />
                  );
                })}
              </g>

              {/* Nodes */}
              {laidOut.map((node, i) => {
                if (node.x === undefined) return null;
                const isActive = activeNode === node.id;
                const isDimmed = connectedIds && !connectedIds.has(node.id) && !isActive;
                const r = Math.max(6, Math.min(18, 5 + node.weight * 0.9));

                return (
                  <g
                    key={node.id}
                    style={{ cursor: "pointer" }}
                    onClick={() => setActiveNode(isActive ? null : node.id)}
                  >
                    {/* Glow */}
                    <motion.circle
                      cx={node.x} cy={node.y} r={r + 6}
                      fill={node.color}
                      opacity={isActive ? 0.25 : 0.06}
                      animate={{ r: isActive ? r + 10 : r + 6 }}
                      transition={{ duration: 0.3 }}
                    />
                    {/* Body */}
                    <motion.circle
                      cx={node.x} cy={node.y} r={r}
                      fill={node.color}
                      opacity={isDimmed ? 0.2 : isActive ? 1 : 0.75}
                      initial={{ r: 0, opacity: 0 }}
                      animate={{ r, opacity: isDimmed ? 0.2 : isActive ? 1 : 0.75 }}
                      transition={{ duration: 0.5, delay: i * 0.02 }}
                      whileHover={{ r: r + 3 }}
                    />
                    {/* Label */}
                    {(node.weight > 2 || isActive) && (
                      <motion.text
                        x={node.x} y={(node.y ?? 0) + r + 14}
                        textAnchor="middle"
                        fontSize={isActive ? 11 : 9}
                        fontWeight={isActive ? "bold" : "normal"}
                        fill={isDimmed ? "#374151" : "#e5e7eb"}
                        opacity={isDimmed ? 0.3 : 1}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: isDimmed ? 0.3 : 1 }}
                        style={{ pointerEvents: "none", fontFamily: "monospace" }}
                      >
                        {node.label}
                      </motion.text>
                    )}
                  </g>
                );
              })}
            </svg>
          )}

          {/* Active node tooltip */}
          <AnimatePresence>
            {activeNode && nodeMap[activeNode] && (
              <motion.div
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 4 }}
                className="absolute bottom-4 left-4 right-4 p-4 rounded-2xl bg-black/80 backdrop-blur-xl border border-white/10 text-[11px] font-mono"
              >
                <span className="text-indigo-400 font-bold uppercase tracking-widest">{nodeMap[activeNode].label}</span>
                <span className="text-gray-500"> · aparece </span>
                <span className="text-white font-bold">{nodeMap[activeNode].weight}×</span>
                <span className="text-gray-500"> · {connectedIds ? connectedIds.size - 1 : 0} conexiones</span>
                <span className="text-gray-600 ml-3 cursor-pointer hover:text-white" onClick={() => setActiveNode(null)}>✕</span>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Timeline panel */}
        <div className="flex flex-col gap-3">
          {/* Search */}
          <div className="relative">
            <Search size={12} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-600" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Filtrar memorias..."
              className="w-full pl-9 pr-4 py-3 rounded-2xl bg-white/5 border border-white/10 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500/50 transition-colors font-mono"
            />
          </div>

          {/* Memory list */}
          <div className="space-y-2 overflow-y-auto max-h-[360px] pr-1 scrollbar-none">
            <AnimatePresence>
              {filtered.length === 0 ? (
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="text-center text-gray-600 text-xs font-mono py-8"
                >
                  {loading ? "Cargando memorias..." : "Sin memorias que coincidan."}
                </motion.p>
              ) : (
                filtered.map((rec, i) => (
                  <TimelineItem
                    key={`${rec.session_id}-${i}`}
                    rec={rec}
                    active={activeRecord?.created_at === rec.created_at}
                    onClick={() => setActiveRecord(activeRecord?.created_at === rec.created_at ? null : rec)}
                  />
                ))
              )}
            </AnimatePresence>
          </div>

          {/* Expanded record detail */}
          <AnimatePresence>
            {activeRecord && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="p-4 rounded-2xl bg-indigo-500/5 border border-indigo-500/20 text-xs text-gray-300 leading-relaxed overflow-hidden"
              >
                <p className="text-[9px] font-mono text-indigo-400 uppercase tracking-widest mb-2">
                  {activeRecord.role === "user" ? "Usuario" : "Aeón"} · {new Date(activeRecord.created_at).toLocaleString()}
                </p>
                {activeRecord.content}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </section>
  );
}

// ── Mock data shown when backend is offline ────────────────────────────────────

const MOCK_DATA: GraphData = {
  nodes: [
    { id: "topic:zana",      label: "zana",      type: "topic", weight: 18, color: "#6366f1" },
    { id: "topic:memoria",   label: "memoria",   type: "topic", weight: 12, color: "#8b5cf6" },
    { id: "topic:docker",    label: "docker",    type: "topic", weight: 9,  color: "#06b6d4" },
    { id: "topic:rust",      label: "rust",      type: "topic", weight: 8,  color: "#ef4444" },
    { id: "topic:modelo",    label: "modelo",    type: "topic", weight: 7,  color: "#f59e0b" },
    { id: "topic:ollama",    label: "ollama",    type: "topic", weight: 6,  color: "#10b981" },
    { id: "topic:search",    label: "search",    type: "topic", weight: 5,  color: "#14b8a6" },
    { id: "topic:vector",    label: "vector",    type: "topic", weight: 5,  color: "#a855f7" },
    { id: "topic:skills",    label: "skills",    type: "topic", weight: 4,  color: "#ec4899" },
    { id: "topic:aeon",      label: "aeon",      type: "topic", weight: 4,  color: "#67e8f9" },
    { id: "topic:install",   label: "install",   type: "topic", weight: 3,  color: "#fbbf24" },
    { id: "topic:agents",    label: "agents",    type: "topic", weight: 3,  color: "#84cc16" },
  ],
  edges: [
    { source: "topic:zana",    target: "topic:memoria",  weight: 4 },
    { source: "topic:zana",    target: "topic:docker",   weight: 3 },
    { source: "topic:zana",    target: "topic:modelo",   weight: 3 },
    { source: "topic:docker",  target: "topic:ollama",   weight: 2 },
    { source: "topic:rust",    target: "topic:vector",   weight: 2 },
    { source: "topic:memoria", target: "topic:vector",   weight: 2 },
    { source: "topic:search",  target: "topic:agents",   weight: 2 },
    { source: "topic:aeon",    target: "topic:skills",   weight: 2 },
  ],
  timeline: [
    { session_id: "demo", role: "user",  content: "¿Cómo configuro Ollama con Docker?", emotion: "curiosity", kalman_surprise: 1.4, created_at: new Date().toISOString() },
    { session_id: "demo", role: "aeon",  content: "Para conectar Ollama desde Docker debes usar host.docker.internal:11434...", emotion: "trust", kalman_surprise: 0.3, created_at: new Date(Date.now() - 60000).toISOString() },
    { session_id: "demo", role: "user",  content: "Instala el paquete de skills para búsqueda semántica", emotion: "joy", kalman_surprise: 2.1, created_at: new Date(Date.now() - 120000).toISOString() },
    { session_id: "demo", role: "aeon",  content: "Ejecutando: zana skills add semantic_search...", emotion: "neutral", kalman_surprise: 0.6, created_at: new Date(Date.now() - 180000).toISOString() },
  ],
  stats: {
    total_analysed: 0,
    topics_extracted: 12,
    edges: 8,
    days_covered: 0,
    dominant_emotion: "curiosity",
  },
};
