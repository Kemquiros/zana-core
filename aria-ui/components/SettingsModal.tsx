'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Settings, ShieldAlert, Trash2, Link2, Database } from 'lucide-react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export default function SettingsModal({ isOpen, onClose }: Props) {
  const [tab, setTab] = useState<'general' | 'apis' | 'danger'>('general');
  const [copied, setCopied] = useState(false);
  
  const [tokens, setTokens] = useState<Record<string, string>>({
    openai: (typeof window !== 'undefined' && localStorage.getItem('token_openai')) || '',
    anthropic: (typeof window !== 'undefined' && localStorage.getItem('token_anthropic')) || '',
    n8n: (typeof window !== 'undefined' && localStorage.getItem('token_n8n')) || '',
    elevenlabs: (typeof window !== 'undefined' && localStorage.getItem('token_elevenlabs')) || '',
  });

  const saveToken = (key: string, val: string) => {
    setTokens(prev => ({ ...prev, [key]: val }));
    localStorage.setItem(`token_${key}`, val);
  };

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
            className="fixed inset-0 bg-black/60 backdrop-blur-md z-[150]"
          />
          <motion.div 
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-2xl bg-[#0a0a0a] border border-white/10 rounded-[3rem] shadow-2xl z-[200] overflow-hidden flex"
          >
            {/* Sidebar */}
            <div className="w-48 border-r border-white/5 p-8 space-y-4">
              <button 
                onClick={() => setTab('general')}
                className={`w-full text-left px-4 py-3 rounded-2xl text-[10px] font-bold uppercase tracking-wider transition-all flex items-center gap-3 ${tab === 'general' ? 'bg-indigo-500 text-white' : 'text-gray-500 hover:bg-white/5'}`}
              >
                <Settings size={14} /> General
              </button>
              <button 
                onClick={() => setTab('apis')}
                className={`w-full text-left px-4 py-3 rounded-2xl text-[10px] font-bold uppercase tracking-wider transition-all flex items-center gap-3 ${tab === 'apis' ? 'bg-indigo-500 text-white' : 'text-gray-500 hover:bg-white/5'}`}
              >
                <Link2 size={14} /> Conexiones
              </button>
              <button 
                onClick={() => setTab('danger')}
                className={`w-full text-left px-4 py-3 rounded-2xl text-[10px] font-bold uppercase tracking-wider transition-all flex items-center gap-3 ${tab === 'danger' ? 'bg-red-500/10 text-red-500 border border-red-500/20' : 'text-red-500/40 hover:text-red-400'}`}
              >
                <ShieldAlert size={14} /> Peligro
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 p-12 relative">
              <button onClick={onClose} className="absolute top-8 right-8 text-gray-500 hover:text-white transition-colors">
                <X size={20} />
              </button>

              {tab === 'general' && (
                <div className="space-y-8">
                  <div className="space-y-2">
                    <h2 className="text-3xl font-black italic uppercase tracking-tighter">Ajustes</h2>
                    <p className="text-sm text-gray-500 font-light">Configuración de presencia y comportamiento.</p>
                  </div>
                  
                  <div className="space-y-4">
                    <div className="p-6 rounded-3xl bg-white/[0.02] border border-white/10 flex items-center justify-between">
                      <div className="space-y-1">
                        <h4 className="text-sm font-bold uppercase tracking-wider">Modo Shadow</h4>
                        <p className="text-[10px] text-gray-500 uppercase tracking-widest">Aeon visible sin fondo al minimizar.</p>
                      </div>
                      <button 
                        onClick={() => {
                          const current = localStorage.getItem('shadow_mode') === 'true';
                          localStorage.setItem('shadow_mode', (!current).toString());
                          window.dispatchEvent(new Event('shadow_mode_change'));
                          setTab('general');
                        }}
                        className={`w-12 h-6 rounded-full transition-all relative ${localStorage.getItem('shadow_mode') === 'true' ? 'bg-indigo-500' : 'bg-white/10'}`}
                      >
                        <div className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-all ${localStorage.getItem('shadow_mode') === 'true' ? 'left-7' : 'left-1'}`} />
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {tab === 'apis' && (
                <div className="space-y-8">
                  <div className="space-y-2">
                    <h2 className="text-3xl font-black italic uppercase tracking-tighter text-indigo-400">Conexiones</h2>
                    <p className="text-sm text-gray-500 font-light">Sincroniza tus llaves maestras con el multiverso.</p>
                  </div>
                  
                  <div className="space-y-4 max-h-[350px] overflow-y-auto pr-2 scrollbar-none">
                    {Object.keys(tokens).map(api => (
                      <div key={api} className="space-y-2">
                        <div className="flex justify-between items-center">
                            <label className="text-[9px] font-mono uppercase tracking-[0.2em] text-gray-500">{api} Token</label>
                            {tokens[api] && <span className="text-[8px] font-black text-green-500 uppercase tracking-widest flex items-center gap-1"><Database size={8}/> Local Encrypted</span>}
                        </div>
                        <input 
                          type="password"
                          value={tokens[api]}
                          onChange={(e) => saveToken(api, e.target.value)}
                          placeholder={`Introduce tu llave de ${api.toUpperCase()}...`}
                          className="w-full bg-white/[0.03] border border-white/10 rounded-2xl p-4 text-xs focus:outline-none focus:border-indigo-500 transition-all font-mono"
                        />
                      </div>
                    ))}
                  </div>

                  <div className="p-5 rounded-2xl bg-indigo-500/5 border border-indigo-500/10">
                    <p className="text-[9px] text-indigo-400 font-mono uppercase tracking-[0.2em] leading-relaxed">
                      ZANA nunca envía tus tokens a nubes de terceros. Se almacenan 100% en tu hardware soberano.
                    </p>
                  </div>
                </div>
              )}

              {tab === 'danger' && (
                <div className="space-y-8 text-center py-8">
                  <div className="w-20 h-20 bg-red-500/10 border border-red-500/20 rounded-full flex items-center justify-center mx-auto text-red-500">
                    <ShieldAlert size={40} />
                  </div>
                  <div className="space-y-2">
                    <h2 className="text-3xl font-black italic uppercase tracking-tighter text-red-500">Desinstalar</h2>
                    <p className="text-sm text-gray-500 max-w-xs mx-auto">Esto borrará permanentemente la conciencia de tu Aeón local.</p>
                  </div>
                  <div className="bg-black/60 rounded-2xl p-4 border border-white/5 flex items-center justify-between gap-4">
                    <code className="text-[10px] text-red-300 font-mono truncate">$ {command}</code>
                    <button onClick={copyCommand} className="shrink-0 p-2 bg-white/5 hover:bg-red-500 hover:text-white rounded-lg transition-all">
                      {copied ? <Check size={14} /> : <Trash2 size={14} />}
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

function Check({ size }: { size: number }) {
    return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className="text-green-400"><polyline points="20 6 9 17 4 12"/></svg>;
}
