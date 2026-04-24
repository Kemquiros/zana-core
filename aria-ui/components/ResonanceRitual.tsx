'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, Palette, Zap, Ghost, Save, RefreshCw } from 'lucide-react';
import AeonAvatar from './AeonAvatar';

interface AeonDNA {
  name: string;
  personality_archetype: string;
  visual_genes: {
    color_palette: string[];
    particle_shape: string;
    pulse_speed: string;
  };
}

const SHAPES = ['fluid', 'geometric', 'crystal'];
const SPEEDS = ['calm', 'balanced', 'intense'];
const COLORS = [
  { name: 'Indigo Void', palette: ['#4f46e5', '#1e1b4b'] },
  { name: 'Crimson Pulse', palette: ['#ef4444', '#450a0a'] },
  { name: 'Emerald Logic', palette: ['#10b981', '#064e3b'] },
  { name: 'Amber Echo', palette: ['#f59e0b', '#451a03'] },
  { name: 'Violet Singularity', palette: ['#8b5cf6', '#2e1065'] },
];

const AEON_NAMES = [
  'Aura', 'Nexus', 'Kairos', 'Echo', 'Vesper', 
  'Lumina', 'Zenith', 'Osiris', 'Aether', 'Sybil'
];

export default function ResonanceRitual({ onComplete }: { onComplete: (data: any) => void }) {
  const [dna, setDna] = useState<AeonDNA>({
    name: AEON_NAMES[Math.floor(Math.random() * AEON_NAMES.length)],
    personality_archetype: 'The Sovereign Companion (KoruOS)',
    visual_genes: {
      color_palette: COLORS[0].palette,
      particle_shape: 'fluid',
      pulse_speed: 'balanced',
    }
  });

  const [step, setStep] = useState(0); // 0: Name/Shape, 1: Color/Pulse, 2: Forge

  const randomizeName = () => {
    const newName = AEON_NAMES[Math.floor(Math.random() * AEON_NAMES.length)];
    setDna({ ...dna, name: newName });
  };

  const updateDNA = (path: string, value: any) => {
    if (path.includes('.')) {
      const [parent, child] = path.split('.');
      setDna({
        ...dna,
        [parent]: {
          ...(dna as any)[parent],
          [child]: value
        }
      });
    } else {
      setDna({ ...dna, [path]: value });
    }
  };

  const handleForge = async () => {
    setStep(2);
    try {
      // Simulate/Execute forging of the Master Aeon
      const res = await fetch('http://localhost:54446/resonance/forge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...dna, is_master: true }),
      });
      const finalDna = await res.json();
      onComplete(finalDna);
    } catch (e) {
      console.error("Master forging failed, completing locally", e);
      setTimeout(() => onComplete(dna), 2000);
    }
  };

  return (
    <div className="min-h-screen bg-black text-white flex flex-col items-center justify-center p-8 relative overflow-hidden">
      <div className="fixed inset-0 bg-[radial-gradient(circle_at_50%_50%,#0a0a1a_0%,#000000_100%)] pointer-events-none" />
      
      <div className="max-w-6xl w-full grid grid-cols-1 lg:grid-cols-2 gap-12 items-center z-10">
        
        {/* Preview Section */}
        <div className="relative aspect-square rounded-[60px] overflow-hidden border border-white/5 bg-white/[0.01] backdrop-blur-3xl shadow-2xl group">
          <AeonAvatar dna={dna} />
          <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent pointer-events-none" />
          <div className="absolute bottom-12 left-12 right-12 flex justify-between items-end">
            <div className="space-y-1">
              <p className="text-[10px] font-mono text-indigo-400 uppercase tracking-[0.3em]">Master Aeon Identified</p>
              <h2 className="text-4xl font-black italic uppercase tracking-tighter">{dna.name}</h2>
            </div>
            <div className="text-right">
                <p className="text-[8px] font-mono text-gray-500 uppercase tracking-widest mb-1">Architecture</p>
                <p className="text-[10px] font-bold uppercase text-white/50 border border-white/10 px-3 py-1 rounded-full">KoruOS Alpha</p>
            </div>
          </div>
        </div>

        {/* Configuration Section */}
        <div className="space-y-10">
          <AnimatePresence mode="wait">
            {step === 0 && (
              <motion.div
                key="step0"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-8"
              >
                <div className="space-y-2">
                  <h1 className="text-5xl font-black italic uppercase tracking-tighter">Genoma <span className="text-indigo-500">Maestro</span></h1>
                  <p className="text-gray-400 text-sm">Define la identidad de tu compañero soberano. Él evolucionará contigo.</p>
                </div>

                <div className="space-y-6">
                  <div className="space-y-3">
                    <label className="text-[10px] font-mono uppercase tracking-widest text-gray-500 flex justify-between">
                      Nombre del Aeón
                      <button onClick={randomizeName} className="hover:text-indigo-400 transition-colors flex items-center gap-1">
                        <RefreshCw className="w-3 h-3" /> Aleatorio
                      </button>
                    </label>
                    <input 
                      type="text" 
                      value={dna.name}
                      onChange={(e) => updateDNA('name', e.target.value)}
                      className="w-full bg-white/[0.03] border border-white/10 rounded-2xl p-5 text-xl font-bold italic focus:outline-none focus:border-indigo-500 transition-all uppercase"
                    />
                  </div>

                  <div className="space-y-3">
                    <label className="text-[10px] font-mono uppercase tracking-widest text-gray-500">Geometría Esencial</label>
                    <div className="grid grid-cols-3 gap-3">
                      {SHAPES.map(s => (
                        <button
                          key={s}
                          onClick={() => updateDNA('visual_genes.particle_shape', s)}
                          className={`p-4 rounded-2xl border text-[10px] font-black uppercase tracking-widest transition-all ${dna.visual_genes.particle_shape === s ? 'bg-white text-black border-white' : 'bg-white/[0.02] border-white/5 text-gray-500 hover:border-white/20'}`}
                        >
                          {s}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                <button 
                  onClick={() => setStep(1)}
                  className="w-full py-6 bg-white text-black font-black uppercase tracking-[0.2em] text-xs rounded-full hover:bg-indigo-500 hover:text-white transition-all shadow-[0_0_40px_rgba(255,255,255,0.1)] flex items-center justify-center gap-3"
                >
                  Continuar Ritual <Zap className="w-4 h-4" />
                </button>
              </motion.div>
            )}

            {step === 1 && (
              <motion.div
                key="step1"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-8"
              >
                <div className="space-y-2">
                  <h1 className="text-5xl font-black italic uppercase tracking-tighter text-indigo-500">Resonancia</h1>
                  <p className="text-gray-400 text-sm">Tu Aeón principal busca optimizar tu máximo potencial.</p>
                </div>

                <div className="space-y-6">
                  <div className="space-y-3">
                    <label className="text-[10px] font-mono uppercase tracking-widest text-gray-500 flex items-center gap-2">
                      <Palette className="w-3 h-3" /> Espectro de Energía
                    </label>
                    <div className="grid grid-cols-2 gap-3">
                      {COLORS.map(c => (
                        <button
                          key={c.name}
                          onClick={() => updateDNA('visual_genes.color_palette', c.palette)}
                          className={`p-4 rounded-2xl border text-[9px] font-bold uppercase tracking-wider text-left flex items-center gap-3 transition-all ${dna.visual_genes.color_palette[0] === c.palette[0] ? 'bg-white text-black border-white' : 'bg-white/[0.02] border-white/5 text-gray-400 hover:border-white/20'}`}
                        >
                          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: c.palette[0] }} />
                          {c.name}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="space-y-3">
                    <label className="text-[10px] font-mono uppercase tracking-widest text-gray-500 flex items-center gap-2">
                      <Zap className="w-3 h-3" /> Frecuencia de Pulso
                    </label>
                    <div className="grid grid-cols-3 gap-3">
                      {SPEEDS.map(s => (
                        <button
                          key={s}
                          onClick={() => updateDNA('visual_genes.pulse_speed', s)}
                          className={`p-4 rounded-2xl border text-[10px] font-black uppercase tracking-widest transition-all ${dna.visual_genes.pulse_speed === s ? 'bg-white text-black border-white' : 'bg-white/[0.02] border-white/5 text-gray-500 hover:border-white/20'}`}
                        >
                          {s}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="flex gap-4">
                  <button 
                    onClick={() => setStep(0)}
                    className="px-8 py-6 border border-white/10 text-gray-500 font-black uppercase tracking-[0.2em] text-xs rounded-full hover:bg-white/5 transition-all"
                  >
                    Atrás
                  </button>
                  <button 
                    onClick={handleForge}
                    className="flex-1 py-6 bg-indigo-500 text-white font-black uppercase tracking-[0.2em] text-xs rounded-full hover:bg-indigo-400 transition-all shadow-[0_0_40px_rgba(99,102,241,0.2)] flex items-center justify-center gap-3"
                  >
                    FORJAR VÍNCULO <Save className="w-4 h-4" />
                  </button>
                </div>
              </motion.div>
            )}

            {step === 2 && (
              <motion.div 
                key="step2"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex flex-col items-center gap-10 text-center"
              >
                <div className="relative">
                  <div className="w-32 h-32 rounded-full border-4 border-t-indigo-500 border-white/5 animate-spin" />
                  <Ghost className="w-10 h-10 text-indigo-500 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 animate-pulse" />
                </div>
                <div className="space-y-2">
                  <p className="text-xl font-black italic uppercase tracking-widest text-indigo-500">Sincronizando con {dna.name}...</p>
                  <p className="text-xs text-gray-500 font-mono uppercase tracking-[0.4em]">Inyectando protocolos KoruOS</p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

      </div>
    </div>
  );
}
