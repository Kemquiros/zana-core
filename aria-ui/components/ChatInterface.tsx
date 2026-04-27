"use client";

import { useState, useEffect } from "react";
import { Send, Sparkles } from "lucide-react";
import ConversationFeed from "./ConversationFeed";
import { Message } from "../lib/zana-stream";
import { useZanaStream } from "../lib/zana-stream";

export default function ChatInterface({ stream }: { stream?: ReturnType<typeof useZanaStream> }) {
  const localStream = useZanaStream("cockpit-session");
  const activeStream = stream || localStream;
  const { connected, aeonState, messages: streamMessages, sendText, connect, disconnect } = activeStream;

  const [input, setInput] = useState("");

  useEffect(() => {
    if (!connected) {
      connect();
    }
  }, [connected, connect]);

  const handleSend = () => {
    if (!input.trim()) return;
    sendText(input.trim());
    setInput("");
  };

  return (
    <div className="flex flex-col h-[500px] bg-white/[0.01] border border-white/5 rounded-[2rem] overflow-hidden backdrop-blur-3xl shadow-2xl">
      <div className="flex-1 overflow-hidden flex flex-col p-4">
        <ConversationFeed messages={streamMessages} />
      </div>
      
      <div className="p-6 bg-black/20 border-t border-white/5 flex gap-4 items-center">
        <div className="relative flex-1">
          <input 
            type="text" 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder={connected ? "Escribe un comando o mensaje..." : "Conectando con el Nexus..."}
            disabled={!connected}
            className="w-full bg-white/5 border border-white/10 rounded-2xl py-4 px-6 text-sm focus:outline-none focus:border-indigo-500 transition-all pr-12 disabled:opacity-50"
          />
          <div className="absolute right-4 top-1/2 -translate-y-1/2 text-indigo-500 opacity-50">
            <Sparkles size={16} />
          </div>
        </div>
        <button 
          onClick={handleSend}
          disabled={!connected || !input.trim()}
          className="p-4 bg-indigo-500 text-white rounded-2xl hover:bg-indigo-400 transition-all shadow-lg shadow-indigo-500/20 disabled:opacity-50"
        >
          <Send size={20} />
        </button>
      </div>
    </div>
  );
}
