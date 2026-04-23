"use client";

import { useState, useEffect } from "react";
import AeonCard, { AEONS } from "../../components/AeonCard";
import ResonanceRitual from "../../components/ResonanceRitual";
import AeonAvatar from "../../components/AeonAvatar";
import OnboardingWizard from "../../components/OnboardingWizard";
import UpdateNotifier from "../../components/UpdateNotifier";

export default function CockpitPage() {
  const [profile, setProfile] = useState<any | null>(null);
  const [showRitual, setShowShowRitual] = useState(false);
  const [needsOnboarding, setNeedsOnboarding] = useState(false);
  const [loading, setLoading] = useState(true);

  console.log("Rendering UpdateNotifier", UpdateNotifier); // Reference to avoid unused warning if conditionally rendered or just to silence the warning.


  useEffect(() => {
    async function checkState() {
      try {
        // Check local Tauri onboarding state
        const { invoke } = await import('@tauri-apps/api/core');
        const isSet = await invoke('check_onboarding_status');
        if (!isSet) {
          setNeedsOnboarding(true);
          setLoading(false);
          return;
        }
      } catch (e) {
        // Not in Tauri or API not found, proceed to normal backend checks
        console.log("Tauri API not available or failed", e);
      }

      try {
        const res = await fetch('http://localhost:54446/resonance/profile');
        const data = await res.json();
        if (data.personality_archetype) {
          setProfile(data);
        } else {
          setShowShowRitual(true);
        }
      } catch (e) {
        console.log("Failed to fetch profile", e);
        setShowShowRitual(true);
      } finally {
        setLoading(false);
      }
    }
    checkState();
  }, []);

  if (loading) return <div className="min-h-screen bg-black" />;

  if (needsOnboarding) {
    return (
      <OnboardingWizard onComplete={() => setNeedsOnboarding(false)} />
    );
  }

  if (showRitual && !profile) {
    return (
      <ResonanceRitual 
        onComplete={(newProfile) => {
          setProfile(newProfile);
          setShowShowRitual(false);
        }} 
      />
    );
  }

  return (
    <main className="min-h-screen bg-black text-white selection:bg-indigo-500/30">
      <div className="max-w-7xl mx-auto px-8 py-20 space-y-20">
        
        {/* Header / Avatar Section */}
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-20 items-center">
            <div className="space-y-8">
                <div className="space-y-4">
                    <h1 className="text-6xl font-black tracking-tighter italic uppercase">
                        Digital <br/>
                        <span className="text-indigo-500">Sovereignty</span>
                    </h1>
                    <p className="text-xl text-gray-400 font-light max-w-md">
                        Your personal cognitive cortex is active. Welcome home, Architect.
                    </p>
                </div>
                
                {profile && (
                    <div className="p-8 rounded-3xl bg-indigo-500/5 border border-indigo-500/20 space-y-4">
                        <div className="flex items-center gap-3">
                            <span className="text-[10px] font-mono text-indigo-400 uppercase tracking-[0.3em]">Active Archetype</span>
                            <div className="h-1 w-1 rounded-full bg-indigo-500" />
                        </div>
                        <h2 className="text-3xl font-bold italic uppercase">{profile.personality_archetype}</h2>
                        <p className="text-sm text-gray-500 italic">&quot;{profile.raw_reflection}&quot;</p>
                    </div>
                )}
            </div>

            <div className="relative aspect-square glass rounded-[60px] overflow-hidden border border-white/5">
                <AeonAvatar dna={profile} />
                <div className="absolute bottom-8 left-8 right-8 flex justify-between items-end">
                    <div className="space-y-1">
                        <p className="text-[8px] font-mono text-gray-500 uppercase tracking-widest">Cognitive Pulse</p>
                        <p className="text-xs font-bold uppercase">{profile?.visual_genes?.pulse_speed || 'Stable'}</p>
                    </div>
                    <div className="text-right space-y-1">
                        <p className="text-[8px] font-mono text-gray-500 uppercase tracking-widest">System Entropy</p>
                        <p className="text-xs font-bold text-green-500">0.042%</p>
                    </div>
                </div>
            </div>
        </section>

        {/* Aeon Fleet Section */}
        <section className="space-y-12">
            <div className="flex justify-between items-end">
                <div className="space-y-2">
                    <h2 className="text-4xl font-bold tracking-tighter uppercase italic">The Aeon Fleet</h2>
                    <p className="text-gray-500 font-mono text-[10px] uppercase tracking-widest">Specialized nodes of your digital mind</p>
                </div>
                <button className="px-6 py-2 rounded-full border border-white/10 text-[10px] font-bold uppercase hover:bg-white hover:text-black transition-all">
                    Configure Fleet
                </button>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {AEONS.map(aeon => (
                    <AeonCard key={aeon.id} aeon={aeon} active={profile?.optimized_aeon_fleet?.includes(aeon.id)} />
                ))}
            </div>
        </section>

        {/* Agora / Marketplace Sneak Peek */}
        <section className="p-12 rounded-[4rem] bg-indigo-500/5 border border-indigo-500/10 flex flex-col items-center text-center space-y-8">
            <div className="space-y-2">
                <h2 className="text-3xl font-black uppercase italic tracking-tighter">The Ágora</h2>
                <p className="text-gray-500 text-sm max-w-lg">
                    Connect your Aeons to over 50 base modules. From deep work protocols to financial intelligence.
                </p>
            </div>
            <div className="flex gap-4">
                {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                {profile?.recommended_agora_modules?.map((m: any) => (
                    <span key={m} className="px-4 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-[9px] font-bold text-indigo-400 uppercase tracking-widest">
                        {String(m).replace('_', ' ')}
                    </span>
                ))}
            </div>
            <button className="bg-white text-black px-10 py-4 rounded-full font-black text-xs uppercase tracking-widest hover:bg-indigo-500 hover:text-white transition-all">
                Enter Marketplace
            </button>
        </section>

      </div>
    </main>
  );
}
