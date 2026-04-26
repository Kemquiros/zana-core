"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Zap, ShieldCheck } from "lucide-react";
import { generateResonancePulse, AionMessage } from "../lib/aion";

export default function AeonVisualizer() {
  const [pulse, setPulse] = useState<AionMessage | null>(null);
  const [history, setHistory] = useState<AionMessage[]>([]);

  useEffect(() => {
    const interval = setInterval(() => {
      // Mock state vector
      const mockState = Array.from({ length: 10 }, () => Math.random());
      const newPulse = generateResonancePulse("AEON_GENESIS_001", mockState);
      setPulse(newPulse);
      setHistory((prev) => [newPulse, ...prev].slice(0, 5));
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="glass-card p-8 rounded-[2.5rem] border-2 border-resonance/20 relative overflow-hidden">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h3 className="text-2xl font-black text-white flex items-center gap-3">
            <div className="w-3 h-3 bg-resonance rounded-full animate-ping" />
            Aeon-Génesis
          </h3>
          <p className="text-slate-500 text-sm font-mono mt-1 tracking-tighter">ID: AEON_GENESIS_001</p>
        </div>
        <div className="px-4 py-1.5 bg-resonance/10 text-resonance rounded-full text-xs font-bold border border-resonance/20">
          AION PROTOCOL v1.0
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
        <div className="flex justify-center py-10">
          <div className="relative w-48 h-48">
            {/* Visual Resonance Sphere */}
            <motion.div
              animate={{ 
                scale: pulse && pulse.innovationScore > 1.2 ? [1, 1.2, 1] : [1, 1.05, 1],
                opacity: pulse && pulse.innovationScore > 1.2 ? 0.8 : 0.4
              }}
              transition={{ duration: 1.5, repeat: Infinity }}
              className="absolute inset-0 bg-gradient-to-br from-resonance to-innovation rounded-full blur-[40px]"
            />
            <div className="absolute inset-0 border-2 border-white/10 rounded-full flex items-center justify-center">
              <Zap className="text-white w-12 h-12" />
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="p-4 bg-black/40 rounded-2xl border border-white/5">
            <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Resonancia Latente</p>
            <div className="flex gap-1">
              {pulse?.latentState.map((val, i) => (
                <motion.div 
                  key={i} 
                  initial={{ height: 0 }}
                  animate={{ height: val * 30 }}
                  className="w-full bg-resonance/60 rounded-sm"
                />
              ))}
            </div>
          </div>

          <div className="space-y-3">
            <AnimatePresence mode="wait">
              {history.map((msg, i) => (
                <motion.div 
                  key={msg.timestamp}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1 - i * 0.2, x: 0 }}
                  exit={{ opacity: 0 }}
                  className="text-[10px] font-mono text-slate-400 flex items-center gap-2"
                >
                  <span className="text-resonance">[{new Date(msg.timestamp).toLocaleTimeString()}]</span>
                  <span className={msg.innovationScore > 1.2 ? "text-innovation font-bold" : ""}>
                    {msg.innovationScore > 1.2 ? "INNOVATION PULSE" : "SYNC"}
                  </span>
                  <span>{msg.innovationScore.toFixed(4)}</span>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </div>
      </div>

      <div className="mt-8 pt-8 border-t border-white/5 flex justify-between items-center text-xs">
        <div className="flex items-center gap-2 text-green-400">
          <ShieldCheck className="w-4 h-4" /> INTEGRIDAD DNA: VERIFICADA
        </div>
        <button className="text-slate-500 hover:text-white transition-colors font-bold uppercase tracking-widest">
          Exportar ADN
        </button>
      </div>
    </div>
  );
}
