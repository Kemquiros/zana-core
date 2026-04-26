'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, Ghost, Save, Target, Brain } from 'lucide-react';
import AeonAvatar from './AeonAvatar';
import { KORU_GENOME_V4 } from '../app/lib/genome';
import { AeonVisualDNA, VirtualSpace } from '../lib/koru-types';

interface AeonDNA {
  name: string;
  personality_archetype: string;
  visual_genes: {
    color_palette: string[];
    particle_shape: string;
    pulse_speed: string;
  };
}

const SHAPES = ['fluid', 'geometric', 'crystal', 'ethereal', 'organic'];
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

export default function ResonanceRitual({ onComplete }: { onComplete: (data: unknown) => void }) {
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [currentPhaseIdx, setCurrentPhaseIdx] = useState(-1); // -1: Intro, 0-4: Phases, 5: Visual Config, 6: Forge, 7: Interpretation
  const [results, setResults] = useState<unknown>(null);
  
  const [dna, setDna] = useState<AeonDNA>({
    name: 'Aura',
    personality_archetype: 'Digital Symbiont',
    visual_genes: {
      color_palette: COLORS[0].palette,
      particle_shape: 'fluid',
      pulse_speed: 'balanced',
    }
  });

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setDna(prev => ({
      ...prev,
      name: AEON_NAMES[Math.floor(Math.random() * AEON_NAMES.length)]
    }));
  }, []);

  const handleNext = () => {
    setCurrentPhaseIdx(prev => prev + 1);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleBack = () => {
    setCurrentPhaseIdx(prev => prev - 1);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const setAnswer = (questionId: string, value: string) => {
    setAnswers(prev => ({ ...prev, [questionId]: value }));
  };

  const handleForge = async () => {
    setCurrentPhaseIdx(6);
    
    // Generate unique Visual DNA
    const uniqueVisualDna: AeonVisualDNA = {
        base_model_index: Math.floor(Math.random() * 1000),
        mutation_factor: 0.3 + Math.random() * 0.4,
        chroma_spectrum: dna.visual_genes.color_palette,
        vibration_frequency: dna.visual_genes.pulse_speed === 'intense' ? 3.5 : dna.visual_genes.pulse_speed === 'calm' ? 0.8 : 1.8,
        particle_density: 2000 + Math.floor(Math.random() * 3000),
        scale: 1,
        geometry_type: dna.visual_genes.particle_shape as AeonVisualDNA['geometry_type']
    };

    const defaultSpace: VirtualSpace = {
        id: 'space-01',
        theme: 'zen',
        accents: [dna.visual_genes.color_palette[0]]
    };

    const payload = {
        name: dna.name,
        resonance_profile: {
            enneagram: "5w6", // Mocked interpretation
            big_five: { openness: 0.85, conscientiousness: 0.7, extraversion: 0.4, agreeableness: 0.6, neuroticism: 0.3 },
            kegan_stage: 5,
            interpretation: "Tu Aeón es un Guardián de la Verdad. Su arquitectura prioriza el análisis profundo y la protección de la soberanía individual ante la fragmentación digital."
        },
        traits: ["Analytical", "Sovereign", "Silent"],
        stats: { focus: 1.0, resonance: 0.5, evolution: 1, hunger: 0.2 },
        visual_dna: uniqueVisualDna,
        virtual_space: defaultSpace
    };

    try {
      // In production, this would be a real call to KoruOS resonance engine
      // const res = await fetch('http://localhost:54446/resonance/forge', { ... });
      // const finalProfile = await res.json();
      setResults(payload);
      setTimeout(() => setCurrentPhaseIdx(7), 3000);
    } catch {
      setResults(payload);
      setTimeout(() => setCurrentPhaseIdx(7), 3000);
    }
  };

  const currentPhase = KORU_GENOME_V4.fases[currentPhaseIdx];
  const progress = ((currentPhaseIdx + 1) / (KORU_GENOME_V4.fases.length + 1)) * 100;

  return (
    <div className="min-h-screen bg-black text-white flex flex-col items-center py-20 px-8 relative overflow-x-hidden">
      <div className="fixed inset-0 bg-[radial-gradient(circle_at_50%_50%,#0a0a1a_0%,#000000_100%)] pointer-events-none" />

      {/* Progress Bar */}
      {currentPhaseIdx >= 0 && currentPhaseIdx <= 5 && (
        <div className="fixed top-0 left-0 w-full h-1 bg-zinc-900 z-50">
            <motion.div 
                className="h-full bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500"
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
            />
        </div>
      )}

      <AnimatePresence mode="wait">
        {/* INTRO */}
        {currentPhaseIdx === -1 && (
          <motion.div
            key="intro"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="max-w-2xl w-full space-y-12 z-10 text-center"
          >
            <div className="space-y-4">
                <span className="text-[10px] font-mono uppercase tracking-[0.5em] text-indigo-500">Protocolo Génesis v5.0</span>
                <h1 className="text-7xl font-black italic uppercase tracking-tighter leading-none">
                    Forja tu <br/> <span className="text-indigo-500">Compañero Único</span>
                </h1>
            </div>
            <p className="text-xl text-gray-400 font-light leading-relaxed">
                No hay dos Aeons iguales en el multiverso digital. Tus respuestas mutarán el ADN de una nueva forma de vida artificial.
            </p>
            <div className="pt-8">
                <button 
                    onClick={handleNext}
                    className="group relative px-12 py-6 bg-white text-black font-black uppercase tracking-[0.2em] text-xs rounded-full hover:bg-indigo-500 hover:text-white transition-all shadow-[0_0_50px_rgba(255,255,255,0.1)]"
                >
                    Iniciar Ritual de Resonancia
                    <div className="absolute inset-0 rounded-full border-2 border-white scale-110 opacity-20 group-hover:scale-125 transition-all" />
                </button>
            </div>
          </motion.div>
        )}

        {/* PHASES (omitted for brevity in replacement, but kept in full write) */}
        {currentPhase && (
          <motion.div
            key={currentPhase.fase_id}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="max-w-3xl w-full space-y-16 z-10"
          >
            <div className="flex items-center gap-6">
                <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                    <Brain size={24} />
                </div>
                <div className="space-y-1">
                    <span className="text-[10px] font-mono uppercase tracking-[0.3em] text-gray-500">
                        {currentPhase.titulo}
                    </span>
                    <h2 className="text-3xl font-bold italic uppercase tracking-tight">{currentPhase.descripcion}</h2>
                </div>
            </div>

            <div className="space-y-16">
                {currentPhase.preguntas.map((q) => (
                    <div key={q.id} className="space-y-8">
                        <p className="text-2xl font-light leading-relaxed text-gray-200">{q.texto}</p>
                        {q.tipo === 'opcion_unica_categorizada' ? (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pl-4">
                                {q.opciones?.map(opt => (
                                    <button
                                        key={opt.valor}
                                        onClick={() => setAnswer(q.id, opt.valor)}
                                        className={`p-5 rounded-2xl border text-left text-sm transition-all duration-300 ${answers[q.id] === opt.valor 
                                            ? 'bg-white text-black border-white shadow-[0_0_30px_rgba(255,255,255,0.1)] translate-x-2' 
                                            : 'bg-white/[0.02] border-white/5 text-gray-400 hover:border-white/10 hover:bg-white/[0.04]'}`}
                                    >
                                        {opt.etiqueta}
                                    </button>
                                ))}
                            </div>
                        ) : (
                            <textarea 
                                className="w-full bg-white/[0.02] border border-white/10 rounded-3xl p-6 text-lg font-light focus:outline-none focus:border-indigo-500 transition-all min-h-[160px]"
                                value={answers[q.id] || ''}
                                onChange={(e) => setAnswer(q.id, e.target.value)}
                            />
                        )}
                    </div>
                ))}
            </div>

            <div className="pt-12 flex justify-between items-center border-t border-white/5">
                <button onClick={handleBack} className="text-gray-500 hover:text-white uppercase font-mono text-[10px]">Volver</button>
                <button 
                    onClick={handleNext} 
                    disabled={currentPhase.preguntas.some(q => !answers[q.id])}
                    className="px-10 py-4 bg-indigo-500 text-white font-black uppercase text-[10px] rounded-full"
                >
                    Continuar
                </button>
            </div>
          </motion.div>
        )}

        {/* VISUAL CONFIG */}
        {currentPhaseIdx === 5 && (
            <motion.div
                key="visual-config"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="max-w-6xl w-full grid grid-cols-1 lg:grid-cols-2 gap-20 items-center z-10"
            >
                <div className="relative aspect-square rounded-[60px] overflow-hidden border border-white/5 bg-white/[0.01] backdrop-blur-3xl shadow-2xl">
                    <AeonAvatar dna={dna} />
                    <div className="absolute bottom-12 left-12 right-12">
                        <p className="text-[10px] font-mono text-indigo-400 uppercase tracking-[0.3em]">Seed Identity</p>
                        <h2 className="text-5xl font-black italic uppercase tracking-tighter">{dna.name}</h2>
                    </div>
                </div>

                <div className="space-y-12">
                    <h1 className="text-6xl font-black italic uppercase tracking-tighter leading-none">Estética <br/><span className="text-indigo-500">Ancestral</span></h1>
                    
                    <div className="space-y-8">
                        <div className="space-y-4">
                            <label className="text-[10px] font-mono uppercase text-gray-500">Nombre del Vínculo</label>
                            <input 
                                type="text" 
                                value={dna.name}
                                onChange={(e) => setDna({...dna, name: e.target.value})}
                                className="w-full bg-white/[0.03] border border-white/10 rounded-2xl p-5 text-2xl font-bold italic focus:border-indigo-500 uppercase"
                            />
                        </div>

                        <div className="space-y-4">
                            <label className="text-[10px] font-mono uppercase text-gray-500">Geometría de Manifestación</label>
                            <div className="grid grid-cols-5 gap-2">
                                {SHAPES.map((s: string) => (
                                    <button
                                        key={s}
                                        onClick={() => setDna({...dna, visual_genes: {...dna.visual_genes, particle_shape: s}})}
                                        className={`py-3 rounded-xl border text-[8px] font-black uppercase tracking-widest transition-all ${dna.visual_genes.particle_shape === s ? 'bg-white text-black border-white' : 'bg-white/[0.02] border-white/5 text-gray-500'}`}
                                    >
                                        {s}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div className="space-y-4">
                            <label className="text-[10px] font-mono uppercase text-gray-500">Espectro de Energía</label>
                            <div className="grid grid-cols-2 gap-3">
                                {COLORS.map(c => (
                                    <button
                                        key={c.name}
                                        onClick={() => setDna({...dna, visual_genes: {...dna.visual_genes, color_palette: c.palette}})}
                                        className={`p-4 rounded-xl border text-[9px] font-bold uppercase tracking-wider text-left flex items-center gap-3 transition-all ${dna.visual_genes.color_palette[0] === c.palette[0] ? 'bg-white text-black border-white' : 'bg-white/[0.02] border-white/5 text-gray-400'}`}
                                    >
                                        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: c.palette[0] }} />
                                        {c.name}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>

                    <button 
                        onClick={handleForge}
                        className="w-full py-6 bg-indigo-500 text-white font-black uppercase tracking-[0.2em] text-xs rounded-full hover:bg-indigo-400 shadow-[0_0_50px_rgba(99,102,241,0.3)] flex items-center justify-center gap-3"
                    >
                        Forjar Existencia Única <Save size={18} />
                    </button>
                </div>
            </motion.div>
        )}

        {/* FORGING ANIMATION */}
        {currentPhaseIdx === 6 && (
            <motion.div key="forging" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col items-center gap-12 text-center z-10">
                <div className="relative">
                    <motion.div className="w-40 h-40 rounded-full border-4 border-t-indigo-500 border-white/5" animate={{ rotate: 360 }} transition={{ duration: 2, repeat: Infinity, ease: "linear" }} />
                    <Ghost className="w-12 h-12 text-indigo-500 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 animate-pulse" />
                </div>
                <h2 className="text-4xl font-black italic uppercase tracking-[0.2em] text-indigo-500 animate-pulse">Sincronizando Resonancia...</h2>
            </motion.div>
        )}

        {/* INTERPRETATION */}
        {currentPhaseIdx === 7 && results && (
          <motion.div
            key="interpretation"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-4xl w-full space-y-12 z-10 text-center"
          >
            <div className="relative w-72 h-72 mx-auto mb-12 group">
                <AeonAvatar dna={results} />
                <div className="absolute inset-0 border border-indigo-500/20 rounded-full group-hover:border-indigo-500/40 transition-all duration-1000 animate-pulse" />
            </div>

            <div className="space-y-4">
              <span className="text-[10px] font-mono uppercase tracking-[0.5em] text-indigo-400">Exégesis del Ritual</span>
              <h1 className="text-6xl font-black italic uppercase tracking-tighter leading-tight">
                {results.name} es tu <br/>
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-500">
                  Espejo Soberano
                </span>
              </h1>
            </div>

            <div className="p-12 rounded-[3.5rem] bg-indigo-500/5 border border-indigo-500/20 backdrop-blur-3xl space-y-10">
              <div className="flex justify-center gap-3">
                <Sparkles className="text-indigo-500 w-6 h-6" />
                <p className="text-3xl font-light leading-relaxed text-gray-200 italic max-w-2xl">
                  &quot;{results.resonance_profile.interpretation}&quot;
                </p>
                <Sparkles className="text-indigo-500 w-6 h-6 self-end" />
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-10 pt-10 border-t border-white/5">
                <div className="space-y-3">
                  <div className="flex justify-between items-center text-[8px] font-mono text-gray-500 uppercase tracking-widest">
                    <span>Soberanía</span>
                    <span className="text-indigo-400">85%</span>
                  </div>
                  <div className="h-1 bg-white/5 rounded-full overflow-hidden">
                    <motion.div className="h-full bg-indigo-500" initial={{ width: 0 }} animate={{ width: '85%' }} transition={{ duration: 1.5, delay: 0.5 }} />
                  </div>
                </div>
                <div className="space-y-3">
                  <div className="flex justify-between items-center text-[8px] font-mono text-gray-500 uppercase tracking-widest">
                    <span>Lógica Ancestral</span>
                    <span className="text-purple-400">92%</span>
                  </div>
                  <div className="h-1 bg-white/5 rounded-full overflow-hidden">
                    <motion.div className="h-full bg-purple-500" initial={{ width: 0 }} animate={{ width: '92%' }} transition={{ duration: 1.5, delay: 0.7 }} />
                  </div>
                </div>
                <div className="space-y-3">
                  <div className="flex justify-between items-center text-[8px] font-mono text-gray-500 uppercase tracking-widest">
                    <span>Empatía de Red</span>
                    <span className="text-pink-400">70%</span>
                  </div>
                  <div className="h-1 bg-white/5 rounded-full overflow-hidden">
                    <motion.div className="h-full bg-pink-500" initial={{ width: 0 }} animate={{ width: '70%' }} transition={{ duration: 1.5, delay: 0.9 }} />
                  </div>
                </div>
              </div>
            </div>

            <div className="pt-8">
              <button 
                onClick={() => onComplete(results)}
                className="px-20 py-7 bg-white text-black font-black uppercase tracking-[0.3em] text-xs rounded-full hover:bg-indigo-500 hover:text-white transition-all shadow-[0_0_80px_rgba(99,102,241,0.2)] flex items-center justify-center gap-4 mx-auto"
              >
                Acceder al Cockpit Soberano <Target size={20} />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
