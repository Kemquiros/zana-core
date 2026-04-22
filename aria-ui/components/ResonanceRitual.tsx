'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, ChevronRight, Check, Zap, Heart, Shield, Cpu, Share2 } from 'lucide-react';

interface RitualResponse {
  personality_archetype: string;
  traits: Record<string, number>;
  visual_genes: {
    color_palette: string[];
    particle_shape: string;
    pulse_speed: string;
  };
  recommended_agora_modules: string[];
}

const RITUAL_DATA = {
  fases: [
    {
      id: 'F1',
      titulo: 'Acto I: La Mente Soberana',
      icon: <Shield className="w-5 h-5" />,
      preguntas: [
        {
          id: 'q1', texto: '¿Cuál es el objetivo primordial de tu Córtex Personal?', tipo: 'opcion', opciones: [
            { valor: 'A', etiqueta: 'Blindaje total: privacidad y disciplina de datos.' },
            { valor: 'E', etiqueta: 'Entendimiento: lógica pura y mapeo de la realidad.' },
            { valor: 'F', etiqueta: 'Evolución: descubrimiento de nuevos algoritmos y libertad.' }
          ]
        },
        {
          id: 'q2', texto: '¿Qué sientes cuando tus datos están en una nube corporativa?', tipo: 'opcion', opciones: [
            { valor: 'A', etiqueta: 'Invasión: mis pensamientos no son un producto.' },
            { valor: 'B', etiqueta: 'Indiferencia: mientras la herramienta funcione.' },
            { valor: 'C', etiqueta: 'Vulnerabilidad: temo perder el rastro de mi memoria.' }
          ]
        }
      ]
    },
    {
      id: 'F2',
      titulo: 'Acto II: El Arquitecto Indie',
      icon: <Cpu className="w-5 h-5" />,
      preguntas: [
        {
          id: 'q6', texto: '¿Cómo visualizas el ensamblaje de tu ZANA?', tipo: 'opcion', opciones: [
            { valor: 'A', etiqueta: 'Como un motor de acero: preciso, frío y robusto.' },
            { valor: 'B', etiqueta: 'Como un organismo vivo: empático y resonante.' },
            { valor: 'C', etiqueta: 'Como un enjambre de caos: creativo y multiforme.' }
          ]
        },
        { id: 'q20_critica', texto: '¿Cuál es la ley inquebrantable que tu Aeon jamás debe violar?', tipo: 'abierta', placeholder: 'Ej: Jamás mentir sobre el origen de un dato...' }
      ]
    }
  ]
};

export default function ResonanceRitual({ onComplete }: { onComplete: (data: RitualResponse) => void }) {
  const [currentFaseIdx, setCurrentFaseIdx] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [isFinishing, setIsFinishing] = useState(false);

  const currentFase = RITUAL_DATA.fases[currentFaseIdx];

  const handleNext = async () => {
    if (currentFaseIdx < RITUAL_DATA.fases.length - 1) {
      setCurrentFaseIdx(currentFaseIdx + 1);
    } else {
      setIsFinishing(true);
      try {
        const res = await fetch('http://localhost:54446/resonance/forge', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ answers }),
        });
        const dna = await res.json();
        onComplete(dna);
      } catch (e) {
        console.error("Forging failed", e);
      } finally {
        setIsFinishing(false);
      }
    }
  };

  return (
    <div className="min-h-screen bg-black text-white flex flex-col items-center py-20 px-8 relative overflow-hidden">
      <div className="fixed inset-0 bg-[radial-gradient(circle_at_50%_50%,#0a0a1a_0%,#000000_100%)] pointer-events-none" />
      
      <AnimatePresence mode="wait">
        {!isFinishing ? (
          <motion.div
            key={currentFaseIdx}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 1.05 }}
            className="max-w-2xl w-full space-y-12 z-10"
          >
            <div className="space-y-2">
                <div className="flex items-center gap-4">
                <div className="p-3 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                    {currentFase.icon}
                </div>
                <h2 className="text-3xl font-black tracking-tighter uppercase italic">{currentFase.titulo}</h2>
                </div>
                <p className="text-[10px] font-mono uppercase tracking-[0.4em] text-gray-500">ZANA_GENESIS_PROTOCOL v2.5</p>
            </div>

            <div className="space-y-12">
              {currentFase.preguntas.map((q) => (
                <div key={q.id} className="space-y-6">
                  <p className="text-xl font-light text-gray-300 italic">"{q.texto}"</p>
                  
                  {q.tipo === 'opcion' ? (
                    <div className="grid grid-cols-1 gap-3">
                      {q.opciones?.map((opt) => (
                        <button
                          key={opt.valor}
                          onClick={() => setAnswers({ ...answers, [q.id]: opt.valor })}
                          className={`p-5 rounded-2xl border text-left text-sm transition-all ${
                            answers[q.id] === opt.valor
                            ? 'bg-white text-black border-white shadow-[0_0_30px_rgba(255,255,255,0.2)]'
                            : 'bg-white/[0.02] border-white/5 text-gray-500 hover:border-white/20'
                          }`}
                        >
                          {opt.etiqueta}
                        </button>
                      ))}
                    </div>
                  ) : (
                    <textarea
                      className="w-full bg-white/[0.02] border border-white/5 rounded-2xl p-6 text-sm focus:outline-none focus:border-indigo-500 transition-all min-h-[120px]"
                      placeholder={q.placeholder}
                      value={answers[q.id] || ''}
                      onChange={(e) => setAnswers({ ...answers, [q.id]: e.target.value })}
                    />
                  )}
                </div>
              ))}
            </div>

            <button
              onClick={handleNext}
              className="w-full py-6 bg-white text-black font-black uppercase tracking-[0.2em] text-xs rounded-full hover:bg-indigo-500 hover:text-white transition-all shadow-[0_0_40px_rgba(255,255,255,0.1)]"
            >
              {currentFaseIdx === RITUAL_DATA.fases.length - 1 ? 'FORJAR SOBERANÍA' : 'CONTINUAR RITUAL'}
            </button>
          </motion.div>
        ) : (
          <motion.div className="flex flex-col items-center gap-8 z-10">
            <div className="w-24 h-24 rounded-full border-4 border-t-indigo-500 border-white/5 animate-spin" />
            <p className="text-sm font-mono uppercase tracking-[0.5em] text-indigo-400">Synthesizing Aeon DNA...</p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
