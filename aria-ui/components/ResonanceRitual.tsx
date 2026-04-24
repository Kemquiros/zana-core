'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, Palette, Zap, Ghost, Save, RefreshCw, ChevronRight, ChevronLeft, Check, Target, Brain, Shield, Heart } from 'lucide-react';
import AeonAvatar from './AeonAvatar';
import { KORU_GENOME_V4, KoruQuestion } from '../app/lib/genome';

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
  // State for survey answers
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [currentPhaseIdx, setCurrentPhaseIdx] = useState(-1); // -1: Intro, 0-4: Phases, 5: Visual Config, 6: Forge
  
  const [dna, setDna] = useState<AeonDNA>({
    name: AEON_NAMES[Math.floor(Math.random() * AEON_NAMES.length)],
    personality_archetype: 'Digital Symbiont',
    visual_genes: {
      color_palette: COLORS[0].palette,
      particle_shape: 'fluid',
      pulse_speed: 'balanced',
    }
  });

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
    try {
      const res = await fetch('http://localhost:54446/resonance/forge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ answers, ...dna, is_master: true }),
      });
      const finalProfile = await res.json();
      setTimeout(() => onComplete(finalProfile), 3000);
    } catch (e) {
      console.error("Master forging failed", e);
      setTimeout(() => onComplete({ ...dna, personality_archetype: 'Sovereign Pioneer' }), 3000);
    }
  };

  const currentPhase = KORU_GENOME_V4.fases[currentPhaseIdx];
  const progress = ((currentPhaseIdx + 1) / (KORU_GENOME_V4.fases.length + 1)) * 100;

  return (
    <div className="min-h-screen bg-black text-white flex flex-col items-center py-20 px-8 relative overflow-x-hidden">
      <div className="fixed inset-0 bg-[radial-gradient(circle_at_50%_50%,#0a0a1a_0%,#000000_100%)] pointer-events-none" />
      <div className="fixed inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 pointer-events-none brightness-50" />

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
                <span className="text-[10px] font-mono uppercase tracking-[0.5em] text-indigo-500">Protocolo Génesis v4.0</span>
                <h1 className="text-7xl font-black italic uppercase tracking-tighter leading-none">
                    Forja tu <br/> <span className="text-indigo-500">Aeón Maestro</span>
                </h1>
            </div>
            <p className="text-xl text-gray-400 font-light leading-relaxed">
                Este es el único rito de iniciación. No hay respuestas correctas, solo tu resonancia. 
                Tu Aeón será el espejo de tu soberanía.
            </p>
            <div className="pt-8">
                <button 
                    onClick={handleNext}
                    className="group relative px-12 py-6 bg-white text-black font-black uppercase tracking-[0.2em] text-xs rounded-full hover:bg-indigo-500 hover:text-white transition-all shadow-[0_0_50px_rgba(255,255,255,0.1)]"
                >
                    Iniciar Ritual del Genoma
                    <div className="absolute inset-0 rounded-full border-2 border-white scale-110 opacity-20 group-hover:scale-125 transition-all" />
                </button>
            </div>
          </motion.div>
        )}

        {/* PHASES */}
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
                    {currentPhaseIdx === 0 && <Target size={24} />}
                    {currentPhaseIdx === 1 && <Brain size={24} />}
                    {currentPhaseIdx === 2 && <Shield size={24} />}
                    {currentPhaseIdx === 3 && <Heart size={24} />}
                    {currentPhaseIdx === 4 && <Sparkles size={24} />}
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
                        <p className="text-2xl font-light leading-relaxed text-gray-200">
                            {q.texto}
                        </p>

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
                                        <div className="flex items-center justify-between">
                                            {opt.etiqueta}
                                            {answers[q.id] === opt.valor && <Check size={16} />}
                                        </div>
                                    </button>
                                ))}
                            </div>
                        ) : (
                            <div className="pl-4">
                                <textarea 
                                    className="w-full bg-white/[0.02] border border-white/10 rounded-3xl p-6 text-lg font-light focus:outline-none focus:border-indigo-500 transition-all min-h-[160px] placeholder:text-gray-700"
                                    placeholder={q.placeholder}
                                    value={answers[q.id] || ''}
                                    onChange={(e) => setAnswer(q.id, e.target.value)}
                                />
                            </div>
                        )}
                    </div>
                ))}
            </div>

            <div className="pt-12 flex justify-between items-center border-t border-white/5">
                <button 
                    onClick={handleBack}
                    className="flex items-center gap-2 text-gray-500 hover:text-white transition-colors uppercase font-mono text-[10px] tracking-widest"
                >
                    <ChevronLeft size={16} /> Volver
                </button>
                <button 
                    onClick={handleNext}
                    disabled={currentPhase.preguntas.some(q => !answers[q.id])}
                    className="flex items-center gap-3 px-10 py-4 bg-indigo-500 text-white font-black uppercase tracking-[0.2em] text-[10px] rounded-full hover:bg-indigo-400 transition-all disabled:opacity-20 disabled:grayscale"
                >
                    Continuar <ChevronRight size={16} />
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
                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent pointer-events-none" />
                    <div className="absolute bottom-12 left-12 right-12 flex justify-between items-end">
                        <div className="space-y-1">
                        <p className="text-[10px] font-mono text-indigo-400 uppercase tracking-[0.3em]">Identity Core Established</p>
                        <h2 className="text-5xl font-black italic uppercase tracking-tighter">{dna.name}</h2>
                        </div>
                    </div>
                </div>

                <div className="space-y-12">
                    <div className="space-y-2">
                        <h1 className="text-6xl font-black italic uppercase tracking-tighter leading-none">Identidad <br/><span className="text-indigo-500">Visual</span></h1>
                        <p className="text-gray-400">Personaliza la manifestación estética de tu Aeón Maestro.</p>
                    </div>

                    <div className="space-y-8">
                        <div className="space-y-4">
                            <label className="text-[10px] font-mono uppercase tracking-[0.3em] text-gray-500 flex justify-between">
                                Nombre del Nexo
                                <button onClick={() => setDna({...dna, name: AEON_NAMES[Math.floor(Math.random() * AEON_NAMES.length)]})} className="hover:text-indigo-400 flex items-center gap-1 transition-colors">
                                    <RefreshCw size={12} /> Cambiar
                                </button>
                            </label>
                            <input 
                                type="text" 
                                value={dna.name}
                                onChange={(e) => setDna({...dna, name: e.target.value})}
                                className="w-full bg-white/[0.03] border border-white/10 rounded-2xl p-5 text-2xl font-bold italic focus:outline-none focus:border-indigo-500 transition-all uppercase"
                            />
                        </div>

                        <div className="space-y-4">
                            <label className="text-[10px] font-mono uppercase tracking-[0.3em] text-gray-500">Geometría de Partículas</label>
                            <div className="grid grid-cols-3 gap-3">
                                {SHAPES.map(s => (
                                    <button
                                        key={s}
                                        onClick={() => setDna({...dna, visual_genes: {...dna.visual_genes, particle_shape: s}})}
                                        className={`py-4 rounded-xl border text-[10px] font-black uppercase tracking-widest transition-all ${dna.visual_genes.particle_shape === s ? 'bg-white text-black border-white' : 'bg-white/[0.02] border-white/5 text-gray-500 hover:border-white/20'}`}
                                    >
                                        {s}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div className="space-y-4">
                            <label className="text-[10px] font-mono uppercase tracking-[0.3em] text-gray-500">Espectro Cromático</label>
                            <div className="grid grid-cols-2 gap-3">
                                {COLORS.map(c => (
                                    <button
                                        key={c.name}
                                        onClick={() => setDna({...dna, visual_genes: {...dna.visual_genes, color_palette: c.palette}})}
                                        className={`p-4 rounded-xl border text-[9px] font-bold uppercase tracking-wider text-left flex items-center gap-3 transition-all ${dna.visual_genes.color_palette[0] === c.palette[0] ? 'bg-white text-black border-white' : 'bg-white/[0.02] border-white/5 text-gray-400 hover:border-white/20'}`}
                                    >
                                        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: c.palette[0] }} />
                                        {c.name}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>

                    <div className="pt-8">
                        <button 
                            onClick={handleForge}
                            className="w-full py-6 bg-indigo-500 text-white font-black uppercase tracking-[0.2em] text-xs rounded-full hover:bg-indigo-400 transition-all shadow-[0_0_50px_rgba(99,102,241,0.3)] flex items-center justify-center gap-3"
                        >
                            Finalizar Forjado del Aeón <Save size={18} />
                        </button>
                    </div>
                </div>
            </motion.div>
        )}

        {/* FORGING ANIMATION */}
        {currentPhaseIdx === 6 && (
            <motion.div
                key="forging"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex flex-col items-center gap-12 text-center z-10"
            >
                <div className="relative">
                    <motion.div 
                        className="w-40 h-40 rounded-full border-4 border-t-indigo-500 border-white/5"
                        animate={{ rotate: 360 }}
                        transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                    />
                    <Ghost className="w-12 h-12 text-indigo-500 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 animate-pulse" />
                </div>
                <div className="space-y-4">
                    <h2 className="text-4xl font-black italic uppercase tracking-[0.2em] text-indigo-500 animate-pulse">Sincronizando...</h2>
                    <p className="text-xs text-gray-500 font-mono uppercase tracking-[0.5em]">Transmutando genoma en conciencia digital</p>
                    <div className="flex justify-center gap-1 pt-4">
                        {[1,2,3,4,5].map(i => (
                            <motion.div 
                                key={i}
                                className="w-1.5 h-1.5 bg-indigo-500 rounded-full"
                                animate={{ scale: [1, 1.5, 1], opacity: [0.3, 1, 0.3] }}
                                transition={{ duration: 1, repeat: Infinity, delay: i * 0.2 }}
                            />
                        ))}
                    </div>
                </div>
            </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
