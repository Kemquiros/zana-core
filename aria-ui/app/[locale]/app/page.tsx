"use client";

import { useCallback, useMemo } from "react";
import { motion } from "framer-motion";
import { Activity, Cpu } from "lucide-react";
import { useZanaStream } from "../../../lib/zana-stream";
import AeonFace from "../../../components/AeonFace";
import ConversationFeed from "../../../components/ConversationFeed";
import SensorBar from "../../../components/SensorBar";

const SESSION_ID = "aria-pwa-001";

export default function AeonCockpit() {
  const { connected, aeonState, messages, sendText, sendAudio, sendImage } = useZanaStream(SESSION_ID);

  const lastAeon = useMemo(
    () => [...messages].reverse().find((m) => m.role === "aeon"),
    [messages],
  );

  const handleImage = useCallback(
    (b64: string, mime: string) => sendImage(b64, mime),
    [sendImage],
  );

  return (
    <main className="h-[100dvh] flex flex-col bg-[#050505] font-sans overflow-hidden text-white relative">
      {/* Grid and ambient effects */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div 
          className="absolute inset-0 opacity-[0.015]"
          style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,0.8) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.8) 1px, transparent 1px)', backgroundSize: '32px 32px' }}
        />
        <div className="absolute top-[-20%] left-[-10%] w-[60%] h-[60%] bg-indigo-600/10 blur-[120px] rounded-full" />
        <div className="absolute bottom-[-15%] right-[-10%] w-[50%] h-[50%] bg-amethyst/10 blur-[100px] rounded-full" />
      </div>

      {/* Futuristic top bar */}
      <header className="relative z-20 flex flex-col px-4 pt-safe-top pb-2 border-b border-indigo-500/10 bg-black/40 backdrop-blur-xl">
        <div className="flex items-center justify-between mt-2">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl p-[1px] shadow-[0_0_20px_rgba(99,102,241,0.2)]">
              <div className="w-full h-full bg-black/80 rounded-[11px] flex items-center justify-center">
                <Cpu className="w-5 h-5 text-indigo-400" />
              </div>
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-black tracking-widest uppercase italic bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">
                ZANA <span className="text-indigo-400">AEON</span>
              </span>
              <span className="text-[9px] font-mono text-gray-500 tracking-[0.2em] uppercase">
                Sovereign Companion
              </span>
            </div>
          </div>

          <div className="flex flex-col items-end gap-1">
            <div className="flex items-center gap-2">
              {aeonState !== "idle" && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="flex items-center gap-1.5 px-2 py-0.5 rounded-full border border-indigo-500/30 bg-indigo-500/10"
                >
                  <Activity className="w-3 h-3 text-indigo-400 animate-pulse" />
                  <span className="text-[9px] font-bold text-indigo-400 tracking-widest uppercase">
                    {aeonState}
                  </span>
                </motion.div>
              )}
            </div>
            
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/5 border border-white/5 backdrop-blur-md">
              {connected ? (
                <>
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]" />
                  <span className="text-[9px] font-bold text-emerald-400 tracking-widest uppercase">LINKED</span>
                </>
              ) : (
                <>
                  <div className="w-1.5 h-1.5 rounded-full bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.8)]" />
                  <span className="text-[9px] font-bold text-red-500 tracking-widest uppercase">OFFLINE</span>
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Cybernetic Face area */}
      <motion.div
        className="relative z-10 flex justify-center w-full"
        animate={{ 
          height: messages.length <= 1 ? "40vh" : "120px",
          marginTop: messages.length <= 1 ? "4rem" : "1rem"
        }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      >
        {/* Holographic projection base */}
        <div className="absolute bottom-0 w-32 h-8 bg-indigo-500/20 blur-xl rounded-[100%]" />
        <div className="absolute bottom-4 w-16 h-1 bg-indigo-400/40 blur-sm rounded-[100%]" />
        
        <motion.div
          animate={{ 
            scale: messages.length <= 1 ? 1.2 : 0.6, 
            opacity: 1,
            y: messages.length <= 1 ? 0 : -20
          }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="relative z-10"
        >
          <AeonFace
            state={aeonState}
            emotion={lastAeon?.emotion}
            surprise={lastAeon?.surprise}
          />
        </motion.div>
      </motion.div>

      {/* Conversation Feed with glassmorphism */}
      <div className="relative z-10 flex-1 overflow-hidden px-4 max-w-2xl w-full mx-auto pb-4">
        {/* Fade gradients for scroll */}
        <div className="absolute top-0 left-0 right-0 h-8 bg-gradient-to-b from-[#050505] to-transparent z-10 pointer-events-none" />
        <div className="h-full rounded-3xl bg-white/[0.01] border border-white/[0.02] shadow-[inset_0_0_40px_rgba(0,0,0,0.5)] overflow-hidden">
          <ConversationFeed messages={messages} />
        </div>
        <div className="absolute bottom-0 left-0 right-0 h-12 bg-gradient-to-t from-[#050505] to-transparent z-10 pointer-events-none" />
      </div>

      {/* Sensor Bar Area */}
      <div className="relative z-20 w-full bg-gradient-to-t from-black via-black/90 to-transparent pt-8 pb-safe-bottom">
        <div className="max-w-2xl w-full mx-auto px-4">
          <SensorBar
            onText={sendText}
            onAudio={sendAudio}
            onImage={handleImage}
            disabled={!connected}
          />
          <div className="flex justify-center items-center gap-4 py-3">
            <div className="h-[1px] w-12 bg-gradient-to-r from-transparent to-indigo-500/30" />
            <p className="text-[9px] text-indigo-400/50 font-mono tracking-[0.4em] uppercase">
              CORTEX LINK ACTIVE
            </p>
            <div className="h-[1px] w-12 bg-gradient-to-l from-transparent to-indigo-500/30" />
          </div>
        </div>
      </div>
    </main>
  );
}