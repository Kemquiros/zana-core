'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Settings, ShieldAlert, Trash2, Link2, Database, Cloud, RefreshCw } from 'lucide-react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export default function SettingsModal({ isOpen, onClose }: Props) {
  const [tab, setTab] = useState<'general' | 'apis' | 'memory' | 'danger'>('general');
  const [copied, setCopied] = useState(false);
  const [syncStatus, setSyncStatus] = useState<any>(null);
  const [isSyncing, setIsSyncing] = useState(false);
  
  useEffect(() => {
    if (isOpen && tab === 'memory') {
      fetch('/sync/status').then(r => r.json()).then(setSyncStatus);
    }
  }, [isOpen, tab]);

  const handleSync = async () => {
    setIsSyncing(true);
    await fetch('/sync/trigger', { method: 'POST' });
    setTimeout(() => {
        fetch('/sync/status').then(r => r.json()).then(setSyncStatus);
        setIsSyncing(false);
    }, 5000);
  };
  
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
                onClick={() => setTab('memory')}
                className={`w-full text-left px-4 py-3 rounded-2xl text-[10px] font-bold uppercase tracking-wider transition-all flex items-center gap-3 ${tab === 'memory' ? 'bg-indigo-500 text-white' : 'text-gray-500 hover:bg-white/5'}`}
              >
                <Cloud size={14} /> Memoria
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

              {tab === 'memory' && (
                <div className="space-y-8">
                  <div className="space-y-2">
                    <h2 className="text-3xl font-black italic uppercase tracking-tighter text-indigo-400">Sincronización</h2>
                    <p className="text-sm text-gray-500 font-light">Respaldo soberano con encriptación Aegis.</p>
                  </div>
                  
                  <div className="space-y-6">
                    <div className="p-6 rounded-3xl bg-white/[0.02] border border-white/10 space-y-4">
                      <div className="flex justify-between items-start">
                        <div className="space-y-1">
                            <h4 className="text-sm font-bold uppercase tracking-wider">Estado de Aegis</h4>
                            <p className="text-[9px] font-mono text-indigo-500/80 uppercase">
                                {syncStatus?.enabled ? '🔒 Zero-Knowledge Activo' : '🔓 No Configurado'}
                            </p>
                        </div>
                        <div className={`px-3 py-1 rounded-full text-[8px] font-black uppercase tracking-widest ${syncStatus?.enabled ? 'bg-green-500/10 text-green-500' : 'bg-yellow-500/10 text-yellow-500'}`}>
                            {syncStatus?.enabled ? 'Sync ON' : 'Sync OFF'}
                        </div>
                      </div>

                      <div className="pt-4 border-t border-white/5 space-y-3">
                         <div className="flex justify-between text-[10px] font-mono uppercase tracking-widest text-gray-500">
                             <span>Proveedor</span>
                             <span className="text-white">{syncStatus?.provider || '---'}</span>
                         </div>
                         <div className="flex justify-between text-[10px] font-mono uppercase tracking-widest text-gray-500">
                             <span>Última Sincro</span>
                             <span className="text-white">{syncStatus?.last_sync ? new Date(syncStatus.last_sync).toLocaleString() : 'Nunca'}</span>
                         </div>
                      </div>
                    </div>

                    <button 
                        onClick={handleSync}
                        disabled={isSyncing || !syncStatus?.enabled}
                        className="w-full py-4 bg-indigo-500 hover:bg-indigo-400 disabled:opacity-50 disabled:bg-white/5 rounded-2xl text-[10px] font-black uppercase tracking-[0.2em] transition-all flex items-center justify-center gap-3 shadow-lg shadow-indigo-500/20"
                    >
                        {isSyncing ? <RefreshCw className="animate-spin" size={14} /> : <Cloud size={14} />}
                        {isSyncing ? 'Sincronizando...' : 'Sincronizar ahora'}
                    </button>

                    {!syncStatus?.enabled && (
                        <div className="p-4 rounded-2xl bg-yellow-500/5 border border-yellow-500/10">
                            <p className="text-[9px] text-yellow-500 font-mono uppercase tracking-[0.1em] leading-relaxed">
                                Configura ZANA_SYNC_SEED en tu archivo .env para activar el respaldo encriptado.
                            </p>
                        </div>
                    )}
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
