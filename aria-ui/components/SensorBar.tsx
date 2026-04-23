"use client";

import { useState, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Mic, MicOff, Send, ImagePlus, ScanLine } from "lucide-react";
import { useAudioCapture } from "../lib/audio-capture";

interface Props {
  onText: (text: string) => void;
  onAudio: (wavB64: string) => void;
  onImage: (b64: string, mime: string) => void;
  disabled?: boolean;
}

export default function SensorBar({ onText, onAudio, onImage, disabled }: Props) {
  const [input, setInput] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const { recording, toggle } = useAudioCapture(onAudio);

  const submit = useCallback(() => {
    const t = input.trim();
    if (!t) return;
    onText(t);
    setInput("");
  }, [input, onText]);

  const handleKey = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        submit();
      }
    },
    [submit],
  );

  const handleFile = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        const result = reader.result as string;
        const b64 = result.split(",")[1];
        onImage(b64, file.type);
      };
      reader.readAsDataURL(file);
      e.target.value = "";
    },
    [onImage],
  );

  return (
    <div className="relative">
      {/* Scanning laser effect when recording */}
      <AnimatePresence>
        {recording && (
          <motion.div 
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "2px" }}
            exit={{ opacity: 0, height: 0 }}
            className="absolute -top-4 left-0 right-0 overflow-hidden"
          >
            <motion.div 
              className="w-full h-full bg-indigo-500 shadow-[0_0_10px_#6366f1]"
              animate={{ x: ["-100%", "100%"] }}
              transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
            />
          </motion.div>
        )}
      </AnimatePresence>

      <div className={`
        relative overflow-hidden rounded-[24px] flex items-center gap-2 p-2 
        border transition-all duration-300
        ${recording 
          ? 'bg-indigo-950/40 border-indigo-500/50 shadow-[0_0_30px_rgba(99,102,241,0.2)]' 
          : 'bg-white/5 border-white/10 hover:border-white/20 backdrop-blur-xl shadow-2xl'
        }
      `}>
        
        {/* Animated background pulse when recording */}
        {recording && (
          <motion.div
            className="absolute inset-0 bg-indigo-500/10"
            animate={{ opacity: [0.3, 0.6, 0.3] }}
            transition={{ duration: 1.5, repeat: Infinity }}
          />
        )}

        {/* Mic Button - The Primary Interaction */}
        <motion.button
          whileTap={{ scale: 0.9 }}
          onClick={toggle}
          disabled={disabled}
          className={`
            relative z-10 w-12 h-12 rounded-[18px] flex items-center justify-center transition-all shrink-0
            ${recording
              ? "bg-red-500/20 text-red-400 border border-red-500/50 shadow-[0_0_15px_rgba(239,68,68,0.5)]"
              : "bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 border border-indigo-500/20"
            }
          `}
        >
          <AnimatePresence mode="wait" initial={false}>
            {recording ? (
              <motion.span key="off" initial={{ scale: 0 }} animate={{ scale: 1 }} exit={{ scale: 0 }}>
                <MicOff className="w-5 h-5" />
              </motion.span>
            ) : (
              <motion.span key="on" initial={{ scale: 0 }} animate={{ scale: 1 }} exit={{ scale: 0 }}>
                <Mic className="w-5 h-5" />
              </motion.span>
            )}
          </AnimatePresence>

          {/* Pulse rings */}
          {recording && (
            <>
              <motion.div className="absolute inset-0 rounded-[18px] border border-red-500" animate={{ scale: [1, 1.5], opacity: [0.8, 0] }} transition={{ duration: 1.5, repeat: Infinity }} />
              <motion.div className="absolute inset-0 rounded-[18px] border border-red-500" animate={{ scale: [1, 1.5], opacity: [0.8, 0] }} transition={{ duration: 1.5, repeat: Infinity, delay: 0.75 }} />
            </>
          )}
        </motion.button>

        {/* Text Input */}
        <div className="relative z-10 flex-1 flex items-center">
          {recording ? (
             <div className="flex-1 flex items-center gap-3 pl-2">
               <ScanLine className="w-4 h-4 text-indigo-400 animate-pulse" />
               <span className="text-xs font-mono font-bold text-indigo-300 uppercase tracking-widest">
                 Capturando Voz...
               </span>
             </div>
          ) : (
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKey}
              disabled={disabled || recording}
              placeholder="Habla con tu Aeon..."
              className="w-full bg-transparent text-sm text-white placeholder:text-gray-500 font-medium outline-none min-w-0 px-3 py-2"
            />
          )}
        </div>

        {/* Action Buttons */}
        <div className="relative z-10 flex items-center gap-2 pr-1 shrink-0">
          <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleFile} />
          
          <AnimatePresence>
            {!recording && (
              <motion.button
                initial={{ opacity: 0, scale: 0.8, width: 0 }}
                animate={{ opacity: 1, scale: 1, width: "auto" }}
                exit={{ opacity: 0, scale: 0.8, width: 0 }}
                onClick={() => fileRef.current?.click()}
                disabled={disabled}
                className="w-10 h-10 rounded-[14px] flex items-center justify-center text-gray-400 hover:text-indigo-400 hover:bg-indigo-500/10 transition-all"
              >
                <ImagePlus className="w-5 h-5" />
              </motion.button>
            )}
          </AnimatePresence>

          <AnimatePresence>
            {(!recording && input.trim()) && (
              <motion.button
                initial={{ opacity: 0, scale: 0.8, width: 0 }}
                animate={{ opacity: 1, scale: 1, width: "auto" }}
                exit={{ opacity: 0, scale: 0.8, width: 0 }}
                whileTap={{ scale: 0.9 }}
                onClick={submit}
                disabled={disabled}
                className="w-10 h-10 rounded-[14px] flex items-center justify-center bg-indigo-500 text-white shadow-[0_0_15px_rgba(99,102,241,0.4)] hover:bg-indigo-400 transition-all"
              >
                <Send className="w-4 h-4 ml-0.5" />
              </motion.button>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}