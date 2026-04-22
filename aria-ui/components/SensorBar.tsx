"use client";

import { useState, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Mic, MicOff, Send, ImagePlus } from "lucide-react";
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
    <div className="relative px-2 pb-2">
      <div className="glass-card rounded-2xl flex items-center gap-2 px-3 py-2 border border-white/10">
        {/* mic button */}
        <motion.button
          whileTap={{ scale: 0.9 }}
          onClick={toggle}
          disabled={disabled}
          className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all shrink-0 ${
            recording
              ? "bg-gold/20 border border-gold/50 text-gold"
              : "hover:bg-white/5 text-slate-400 hover:text-white"
          }`}
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
        </motion.button>

        {/* recording indicator */}
        {recording && (
          <motion.div
            initial={{ opacity: 0, width: 0 }}
            animate={{ opacity: 1, width: "auto" }}
            className="shrink-0 flex items-center gap-1.5 text-gold text-xs font-bold"
          >
            <motion.div
              animate={{ opacity: [1, 0, 1] }}
              transition={{ duration: 1, repeat: Infinity }}
              className="w-2 h-2 rounded-full bg-gold"
            />
            REC
          </motion.div>
        )}

        {/* text input */}
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKey}
          disabled={disabled || recording}
          placeholder={recording ? "Grabando audio…" : "Escribe un mensaje…"}
          className="flex-1 bg-transparent text-sm text-white placeholder:text-slate-600 outline-none min-w-0 py-1"
        />

        {/* image upload */}
        <button
          onClick={() => fileRef.current?.click()}
          disabled={disabled}
          className="w-10 h-10 rounded-xl flex items-center justify-center text-slate-400 hover:text-white hover:bg-white/5 transition-all shrink-0"
        >
          <ImagePlus className="w-5 h-5" />
        </button>
        <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleFile} />

        {/* send */}
        <motion.button
          whileTap={{ scale: 0.9 }}
          onClick={submit}
          disabled={disabled || !input.trim()}
          className="w-10 h-10 rounded-xl flex items-center justify-center bg-resonance/80 hover:bg-resonance text-white transition-all shrink-0 disabled:opacity-30 disabled:cursor-not-allowed"
        >
          <Send className="w-4 h-4" />
        </motion.button>
      </div>
    </div>
  );
}
