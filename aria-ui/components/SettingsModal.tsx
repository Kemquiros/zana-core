'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Settings, ShieldAlert, TerminalSquare, Trash2, ArrowRight } from 'lucide-react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export default function SettingsModal({ isOpen, onClose }: Props) {
  const [tab, setTab] = useState<'general' | 'danger'>('general');
  const [copied, setCopied] = useState(false);

  const command = "curl -sL https://raw.githubusercontent.com/kemquiros/zana-core/main/uninstall.sh | bash";

  const copyCommand = () => {
    navigator.clipboard.writeText(command);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[150]"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[90%] max-w-2xl bg-[#0a0a0a] border border-white/10 rounded-3xl overflow-hidden shadow-2xl z-[200] flex min-h-[400px]"
          >
            {/* Sidebar */}
            <div className="w-48 bg-white/[0.02] border-r border-white/5 p-4 space-y-2">
              <div className="px-3 py-2 mb-4">
                <h3 className="text-xs font-black uppercase tracking-widest text-gray-400">Settings</h3>
              </div>
              <button 
                onClick={() => setTab('general')}
                className={`w-full text-left px-3 py-2 rounded-xl text-xs font-bold uppercase tracking-wider transition-all flex items-center gap-2 ${tab === 'general' ? 'bg-indigo-500 text-white' : 'text-gray-400 hover:bg-white/5 hover:text-white'}`}
              >
                <Settings className="w-3 h-3" /> General
              </button>
              <button 
                onClick={() => setTab('danger')}
                className={`w-full text-left px-3 py-2 rounded-xl text-xs font-bold uppercase tracking-wider transition-all flex items-center gap-2 ${tab === 'danger' ? 'bg-red-500/10 text-red-500 border border-red-500/20' : 'text-red-500/50 hover:bg-red-500/5 hover:text-red-400'}`}
              >
                <ShieldAlert className="w-3 h-3" /> Peligro
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 p-8 relative">
              <button onClick={onClose} className="absolute top-4 right-4 p-2 rounded-full hover:bg-white/10 text-gray-500 hover:text-white transition-all">
                <X className="w-4 h-4" />
              </button>

              {tab === 'general' && (
                <div className="space-y-6">
                  <h2 className="text-2xl font-black italic uppercase tracking-tighter">Configuración</h2>
                  <p className="text-sm text-gray-400">Gestiona la conexión al Córtex y LLMs externos.</p>
                  <div className="p-6 border border-white/10 rounded-2xl bg-white/[0.01]">
                    <p className="text-xs text-gray-500 font-mono text-center">Panel de ajustes en construcción.</p>
                  </div>
                </div>
              )}

              {tab === 'danger' && (
                <div className="space-y-6">
                  <div className="space-y-2">
                    <h2 className="text-2xl font-black italic uppercase tracking-tighter text-red-500">Protocolo de Desinstalación</h2>
                    <p className="text-xs text-gray-400 leading-relaxed">
                      ZANA opera a nivel de sistema. Para garantizar una desinstalación segura, incluyendo demonios nativos, librerías compartidas (C/Rust) y datos locales, el proceso debe invocarse desde la terminal.
                    </p>
                  </div>

                  <div className="p-5 border border-red-500/20 bg-red-500/5 rounded-2xl space-y-4">
                    <div className="flex items-center gap-3 text-red-400">
                      <Trash2 className="w-5 h-5" />
                      <div>
                        <h4 className="text-sm font-bold uppercase tracking-wider">Desinstalador Automatizado</h4>
                        <p className="text-[10px] uppercase font-mono tracking-widest opacity-70">Opciones: Seguro o Erradicación Total</p>
                      </div>
                    </div>
                    
                    <div className="relative group">
                      <div className="absolute inset-0 bg-gradient-to-r from-red-500/20 to-transparent blur-md opacity-0 group-hover:opacity-100 transition-opacity" />
                      <div className="relative bg-black border border-white/10 rounded-xl p-4 font-mono text-[10px] text-gray-300 overflow-x-auto">
                        <div className="flex items-center gap-3">
                          <TerminalSquare className="w-4 h-4 text-gray-500 shrink-0" />
                          <span className="select-all">{command}</span>
                        </div>
                      </div>
                    </div>

                    <button 
                      onClick={copyCommand}
                      className="w-full py-3 bg-red-500 text-white rounded-xl text-[10px] font-black uppercase tracking-[0.2em] hover:bg-red-400 transition-all flex items-center justify-center gap-2"
                    >
                      {copied ? 'Comando Copiado' : 'Copiar Comando de Terminal'} <ArrowRight className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
