'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { check } from '@tauri-apps/plugin-updater';
import { relaunch } from '@tauri-apps/plugin-process';
import { ArrowUpCircle, RefreshCw, X, Sparkles } from 'lucide-react';

interface UpdateInfo {
  version: string;
  downloadAndInstall: () => Promise<void>;
}

export default function UpdateNotifier() {
  const [update, setUpdate] = useState<UpdateInfo | null>(null);
  const [status, setStatus] = useState<'idle' | 'checking' | 'downloading' | 'ready'>('idle');
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    async function checkForUpdates() {
      try {
        setStatus('checking');
        const update = await check();
        if (update) {
          setUpdate(update);
          setVisible(true);
          setStatus('idle');
        }
      } catch (e) {
        console.error('Failed to check for updates', e);
        setStatus('idle');
      }
    }

    // Check once on mount, then every 4 hours
    checkForUpdates();
    const interval = setInterval(checkForUpdates, 4 * 60 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const handleUpdate = async () => {
    if (!update) return;
    try {
      setStatus('downloading');
      await update.downloadAndInstall();
      setStatus('ready');
      // Show ready state for a moment before relaunching
      setTimeout(async () => {
        await relaunch();
      }, 1500);
    } catch (e) {
      console.error('Update failed', e);
      setStatus('idle');
    }
  };

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0, y: 50, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 20, scale: 0.9 }}
          className="fixed bottom-8 right-8 z-[100] max-w-sm w-full"
        >
          <div className="relative overflow-hidden rounded-3xl bg-indigo-600/10 border border-indigo-500/30 backdrop-blur-2xl shadow-2xl p-6 space-y-4 group">
            {/* Ambient glow */}
            <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-purple-500/5 pointer-events-none" />
            
            <div className="flex items-start justify-between relative z-10">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-indigo-500/20 text-indigo-400">
                  {status === 'downloading' ? <RefreshCw className="w-5 h-5 animate-spin" /> : <ArrowUpCircle className="w-5 h-5" />}
                </div>
                <div>
                  <h4 className="text-sm font-black uppercase italic tracking-tighter text-white">Actualización Disponible</h4>
                  <p className="text-[10px] font-mono text-indigo-400/70 uppercase tracking-widest">v{update?.version} está lista</p>
                </div>
              </div>
              <button 
                onClick={() => setVisible(false)}
                className="p-1.5 hover:bg-white/5 rounded-lg text-gray-500 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-gray-400 leading-relaxed relative z-10 pl-1">
              {status === 'downloading' 
                ? 'Descargando e instalando el nuevo córtex...' 
                : status === 'ready'
                  ? 'Reinicio inminente. El futuro se está cargando.'
                  : 'Mejoras en el motor de razonamiento y evolución de Aeons disponibles.'}
            </p>

            <div className="flex gap-2 pt-2 relative z-10">
              {status !== 'ready' && (
                <button
                  disabled={status === 'downloading'}
                  onClick={handleUpdate}
                  className="flex-1 py-3 px-4 bg-white text-black rounded-xl text-[10px] font-bold uppercase tracking-widest hover:bg-indigo-500 hover:text-white transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {status === 'downloading' ? 'Descargando...' : (
                    <>
                      Actualizar Ahora <Sparkles className="w-3 h-3" />
                    </>
                  )}
                </button>
              )}
              {status === 'idle' && (
                <button
                  onClick={() => setVisible(false)}
                  className="px-4 py-3 border border-white/5 text-gray-500 rounded-xl text-[10px] font-bold uppercase tracking-widest hover:bg-white/5 transition-all"
                >
                  Más tarde
                </button>
              )}
            </div>

            {/* Loading bar for download */}
            {status === 'downloading' && (
              <div className="absolute bottom-0 left-0 right-0 h-1 bg-white/5">
                <motion.div 
                  className="h-full bg-indigo-500 shadow-[0_0_10px_rgba(99,102,241,0.5)]"
                  initial={{ width: 0 }}
                  animate={{ width: '100%' }}
                  transition={{ duration: 15, ease: "linear" }}
                />
              </div>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
