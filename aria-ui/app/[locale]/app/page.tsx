"use client";

import { useCallback, useMemo } from "react";
import { motion } from "framer-motion";
import { Layers, Activity, Wifi, WifiOff } from "lucide-react";
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
    <main className="h-[100dvh] flex flex-col bg-black font-sans overflow-hidden">
      {/* ambient blobs */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-[-15%] left-[-10%] w-[45%] h-[45%] bg-resonance/10 blur-[100px] rounded-full" />
        <div className="absolute bottom-[-15%] right-[-10%] w-[45%] h-[45%] bg-innovation/10 blur-[100px] rounded-full" />
      </div>

      {/* top bar */}
      <header className="relative z-10 flex items-center justify-between px-5 py-3 border-b border-white/5">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 bg-gradient-to-br from-resonance to-innovation rounded-lg flex items-center justify-center">
            <Layers className="w-4 h-4 text-white" />
          </div>
          <span className="text-sm font-bold text-white tracking-tight">
            ZANA <span className="text-innovation">AEON</span>
          </span>
        </div>

        <div className="flex items-center gap-3 text-xs font-bold">
          <span
            className="flex items-center gap-1.5 uppercase tracking-widest"
            style={{ color: connected ? "#4ADE80" : "#ef4444" }}
          >
            {connected ? <Wifi className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
            {connected ? "ONLINE" : "OFFLINE"}
          </span>
          {aeonState !== "idle" && (
            <motion.span
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex items-center gap-1 text-innovation"
            >
              <Activity className="w-3.5 h-3.5" />
              {aeonState.toUpperCase()}
            </motion.span>
          )}
        </div>
      </header>

      {/* center face — collapses when messages exist */}
      <motion.div
        className="relative z-10 flex justify-center"
        animate={{ paddingTop: messages.length <= 1 ? "2rem" : "0.75rem", paddingBottom: messages.length <= 1 ? "1.5rem" : "0.5rem" }}
        transition={{ duration: 0.4 }}
      >
        <motion.div
          animate={{ scale: messages.length <= 1 ? 1 : 0.65, opacity: 1 }}
          transition={{ duration: 0.4 }}
        >
          <AeonFace
            state={aeonState}
            emotion={lastAeon?.emotion}
            surprise={lastAeon?.surprise}
          />
        </motion.div>
      </motion.div>

      {/* conversation feed */}
      <div className="relative z-10 flex-1 overflow-hidden px-3 max-w-2xl w-full mx-auto">
        <ConversationFeed messages={messages} />
      </div>

      {/* sensor bar */}
      <div className="relative z-10 max-w-2xl w-full mx-auto pb-safe">
        <SensorBar
          onText={sendText}
          onAudio={sendAudio}
          onImage={handleImage}
          disabled={!connected}
        />
        <p className="text-center text-[10px] text-slate-700 font-mono py-1.5 tracking-widest">
          ZANA · NODO SENSORIAL · {SESSION_ID}
        </p>
      </div>
    </main>
  );
}
