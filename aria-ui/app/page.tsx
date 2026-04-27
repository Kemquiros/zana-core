"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import AeonCard, { AEONS } from "../components/AeonCard";
import ResonanceRitual from "../components/ResonanceRitual";
import AeonAvatar from "../components/AeonAvatar";
import OnboardingWizard from "../components/OnboardingWizard";
import ChatInterface from "../components/ChatInterface";
import SettingsModal from "../components/SettingsModal";
import { Settings, ExternalLink, Activity, Zap, Heart, Brain, Star } from "lucide-react";

export default function CockpitPage() {
  const [profile, setProfile] = useState<any | null>(null);
  const [showRitual, setShowShowRitual] = useState(false);
  const [needsOnboarding, setNeedsOnboarding] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showSettings, setShowSettings] = useState(false);
  const [shadowMode, setShadowMode] = useState(false);
  const [koruStatus, setKoruStatus] = useState<'connected' | 'disconnected'>('disconnected');

  useEffect(() => {
    // Default shadow mode to false on first load to prevent "invisible UI" confusion
    if (localStorage.getItem('shadow_mode') === null) {
      localStorage.setItem('shadow_mode', 'false');
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setShadowMode(localStorage.getItem('shadow_mode') === 'true');
    const handleShadowChange = () => setShadowMode(localStorage.getItem('shadow_mode') === 'true');
    window.addEventListener('shadow_mode_change', handleShadowChange);
    return () => window.removeEventListener('shadow_mode_change', handleShadowChange);
  }, []);

  const themeColors: Record<string, string> = {
    zen: 'from-emerald-900/20',
    cyber: 'from-cyan-900/20',
    void: 'from-zinc-900/40',
    nebula: 'from-purple-900/30',
    crystal: 'from-blue-900/20',
    forest: 'from-green-900/20',
    forge: 'from-orange-900/20',
    shrine: 'from-red-900/20',
    oasis: 'from-teal-900/20',
    abyss: 'from-indigo-900/40',
  };

  useEffect(() => {
    const eventSource = new EventSource('http://localhost:51112/ai/forge/genome/stream');

    eventSource.onmessage = () => {
      setKoruStatus('connected');
    };

    eventSource.onerror = () => {
      setKoruStatus('disconnected');
    };

    return () => {
      eventSource.close();
    };
  }, []);

  useEffect(() => {
    async function checkState() {
      try {
        const { invoke } = await import('@tauri-apps/api/core');
        const isSet = await invoke('check_onboarding_status');
        if (!isSet) {
          setNeedsOnboarding(true);
          setLoading(false);
          return;
        }
      } catch (e) {
        console.log("Tauri API not available", e);
      }

      try {
        const res = await fetch('/resonance/profile');
        const data = await res.json();
        if (data.personality_archetype) {
          setProfile(data);
        } else {
          setShowShowRitual(true);
        }
      } catch {
        setShowShowRitual(true);
      } finally {
        setLoading(false);
      }
    }
    checkState();
  }, []);

  const openKoruDashboard = () => {
    window.open('http://localhost:51111', '_blank');
  };
  const currentTheme = profile?.virtual_space?.theme || 'abyss';

  if (loading) return <div className="min-h-screen bg-black" />;
  if (needsOnboarding) return <OnboardingWizard onComplete={() => setNeedsOnboarding(false)} />;
  if (showRitual && !profile) return <ResonanceRitual onComplete={(newProfile) => { setProfile(newProfile); setShowShowRitual(false); }} />;

  return (
    <main className={`min-h-screen text-white selection:bg-indigo-500/30 transition-all duration-700 ${shadowMode ? 'bg-transparent' : 'bg-black'}`}>
      
      {!shadowMode && (
          <div className="fixed inset-0 pointer-events-none overflow-hidden">
              <div className={`absolute inset-0 bg-gradient-to-br ${themeColors[currentTheme]} via-black to-black transition-all duration-1000`} />
              <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 brightness-50" />
              
              {/* Dynamic Aura Glow */}
              <div className="absolute top-1/4 -right-1/4 w-[800px] h-[800px] bg-indigo-500/10 rounded-full blur-[120px] animate-pulse" />
              <div className="absolute -bottom-1/4 -left-1/4 w-[600px] h-[600px] bg-purple-500/5 rounded-full blur-[100px]" />
          </div>
      )}

      <div className={`max-w-7xl mx-auto px-8 py-20 space-y-24 transition-opacity duration-700 relative z-10 ${shadowMode ? 'opacity-0 pointer-events-none' : 'opacity-100'}`}>
        
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-20 items-start">
            <div className="space-y-12">
                <div className="space-y-6">
                    <div className="flex items-center gap-4">
                      <button 
                        onClick={openKoruDashboard}
                        className={`px-4 py-2 rounded-xl border flex items-center gap-2 transition-all ${
                          koruStatus === 'connected' ? 'bg-green-500/10 border-green-500/30 text-green-400' : 'bg-red-500/10 border-red-500/30 text-red-400'
                        }`}
                      >
                        <Activity size={14} className={koruStatus === 'connected' ? 'animate-pulse' : ''} />
                        <span className="text-[10px] font-black uppercase tracking-widest">
                          {koruStatus === 'connected' ? 'Cuerpo Online' : 'Cuerpo Offline'}
                        </span>
                        <ExternalLink size={12} className="opacity-50" />
                      </button>
                    </div>
                    <h1 className="text-7xl font-black tracking-tighter italic uppercase leading-none">
                        {profile?.name || 'ZANA'} <br/>
                        <span className="text-indigo-500">Sovereignty</span>
                    </h1>
                </div>
                
                <div className="space-y-6">
                  <div className="flex items-center gap-3">
                    <span className="text-[10px] font-mono text-gray-500 uppercase tracking-[0.4em]">Canal de Comunicación</span>
                    <div className="h-px flex-1 bg-white/5" />
                  </div>
                  <ChatInterface />
                </div>
            </div>

            <div className="space-y-8 lg:sticky lg:top-20 relative z-0">
              <div className="relative aspect-square glass rounded-[60px] overflow-hidden border border-white/5 shadow-2xl shadow-indigo-500/10">
                  <AeonAvatar dna={profile} />
                  <div className="absolute bottom-8 left-8 right-8 flex justify-between items-end">
                      <div className="space-y-1">
                          <p className="text-[8px] font-mono text-indigo-400 uppercase tracking-widest">Resonancia Activa</p>
                          <p className="text-xs font-bold uppercase">{profile?.personality_archetype || 'Sincronizando...'}</p>
                      </div>
                      <div className="text-right space-y-1">
                          <p className="text-[8px] font-mono text-gray-500 uppercase tracking-widest">Entropía</p>
                          <p className="text-xs font-bold text-green-500">0.042%</p>
                      </div>
                  </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                  <div className="p-6 rounded-3xl bg-white/[0.02] border border-white/10 space-y-4">
                      <div className="flex items-center justify-between">
                          <Zap size={16} className="text-yellow-500" />
                          <span className="text-[8px] font-mono text-gray-500 uppercase">Enfoque</span>
                      </div>
                      <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                          <motion.div className="h-full bg-yellow-500" animate={{ width: `${(profile?.stats?.focus ?? 0.8) * 100}%` }} />
                      </div>
                  </div>
                  <div className="p-6 rounded-3xl bg-white/[0.02] border border-white/10 space-y-4">
                      <div className="flex items-center justify-between">
                          <Heart size={16} className="text-pink-500" />
                          <span className="text-[8px] font-mono text-gray-500 uppercase">Vínculo</span>
                      </div>
                      <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                          <motion.div className="h-full bg-pink-500" animate={{ width: `${(profile?.stats?.resonance ?? 0.5) * 100}%` }} />
                      </div>
                  </div>
                  <div className="p-6 rounded-3xl bg-white/[0.02] border border-white/10 space-y-4">
                      <div className="flex items-center justify-between">
                          <Brain size={16} className="text-indigo-500" />
                          <span className="text-[8px] font-mono text-gray-500 uppercase">Evolución</span>
                      </div>
                      <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                          <motion.div className="h-full bg-indigo-500" animate={{ width: `${(profile?.stats?.evolution ?? 12) % 100}%` }} />
                      </div>
                  </div>
                  <div className="p-6 rounded-3xl bg-white/[0.02] border border-white/10 space-y-4">
                      <div className="flex items-center justify-between">
                          <Star size={16} className="text-cyan-500" />
                          <span className="text-[8px] font-mono text-gray-500 uppercase">Conocimiento</span>
                      </div>
                      <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                          <motion.div className="h-full bg-cyan-500" animate={{ width: `${100 - (profile?.stats?.hunger ?? 0.2) * 100}%` }} />
                      </div>
                  </div>
              </div>

              {/* Sovereign Telemetry Panel */}
              <div className="p-8 rounded-[2rem] bg-white/[0.02] border border-white/10 space-y-6 font-mono text-[10px]">
                <div className="flex items-center justify-between text-gray-500">
                  <span className="tracking-[0.2em]">TELEMETRÍA DE AEÓN</span>
                  <span className="text-indigo-500 animate-pulse">NEXO LIVE</span>
                </div>
                <div className="space-y-3 text-gray-400 max-h-40 overflow-y-auto scrollbar-none">
                  <div className="flex gap-4"><span className="text-indigo-800">[INFO]</span> <span>Capa episódica sincronizada con Obsidian.</span></div>
                  <div className="flex gap-4"><span className="text-indigo-800">[INFO]</span> <span>Patrón detectado: Desarrollo de soberanía activo.</span></div>
                  {koruStatus === 'connected' ? (
                    <div className="flex gap-4 text-green-500/80"><span className="text-green-800">[OK]</span> <span>Cuerpo KoruOS respondiendo en puerto 51112.</span></div>
                  ) : (
                    <div className="flex gap-4 text-red-500/80"><span className="text-red-800">[FAIL]</span> <span>Error de puente: KoruOS no detectado.</span></div>
                  )}
                  <div className="flex gap-4"><span className="text-indigo-800">[INFO]</span> <span>Memoria vectorial: ChromaDB lista para ingestión.</span></div>
                </div>
              </div>
            </div>
        </section>

        <section className="space-y-12">
            <div className="flex justify-between items-end border-b border-white/5 pb-8">
                <div className="space-y-2">
                    <h2 className="text-5xl font-black tracking-tighter uppercase italic">Tu Flota de Aeons</h2>
                    <p className="text-gray-500 font-mono text-[10px] uppercase tracking-[0.3em]">Nodos especializados de tu mente digital</p>
                </div>
                <button className="px-8 py-3 rounded-full bg-white/5 border border-white/10 text-[10px] font-black uppercase tracking-widest hover:bg-white hover:text-black transition-all">
                    Configurar Flota
                </button>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {AEONS.map(aeon => (
                    <AeonCard key={aeon.id} aeon={aeon} active={profile?.optimized_aeon_fleet?.includes(aeon.id)} />
                ))}
            </div>
        </section>

        <section className="space-y-10">
            <div className="space-y-2 text-center">
                <h2 className="text-3xl font-black uppercase italic tracking-tighter">Espacio Virtual</h2>
                <p className="text-gray-500 text-sm">El santuario donde habita tu Aeón Maestro.</p>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                {['zen', 'cyber', 'void', 'nebula', 'crystal', 'forest', 'forge', 'shrine', 'oasis', 'abyss'].map(theme => (
                    <button 
                        key={theme}
                        className={`p-6 rounded-3xl border transition-all uppercase text-[8px] font-black tracking-[0.2em] ${profile?.virtual_space?.theme === theme ? 'bg-indigo-500 border-white text-white' : 'bg-white/5 border-white/5 text-gray-500 hover:border-white/20'}`}
                    >
                        {theme}
                    </button>
                ))}
            </div>
        </section>

      </div>

      <button 
        onClick={() => setShowSettings(true)}
        className="fixed bottom-12 left-12 p-6 rounded-[2rem] bg-white/5 border border-white/10 text-gray-400 hover:text-white hover:bg-white/10 transition-all z-[100] backdrop-blur-xl shadow-2xl"
      >
        <Settings className="w-6 h-6" />
      </button>

      <SettingsModal isOpen={showSettings} onClose={() => setShowSettings(false)} />

      {shadowMode && (
        <div 
          className="fixed inset-0 flex flex-col items-center justify-center z-[300] bg-black/60 backdrop-blur-md cursor-pointer"
          onClick={() => {
            setShadowMode(false);
            localStorage.setItem('shadow_mode', 'false');
          }}
        >
          <div className="w-[500px] aspect-square animate-float pointer-events-none">
            <AeonAvatar dna={profile} />
          </div>
          <p className="text-white/50 text-[10px] font-mono uppercase tracking-[0.3em] mt-8 pointer-events-none animate-pulse">
            Click para despertar
          </p>
        </div>
      )}
    </main>
  );
}
