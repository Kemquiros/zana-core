"use client";

import { useState } from "react";
import { Send, Sparkles } from "lucide-react";
import ConversationFeed from "./ConversationFeed";
import { Message } from "../lib/zana-stream";

export default function ChatInterface() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>(() => [
    { id: "1", role: "aeon", text: "Bienvenido al nexo. Estoy lista para sincronizarnos.", emotion: "trust", timestamp: Date.now() }
  ]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      text: input,
      timestamp: Date.now()
    };

    setMessages(prev => [...prev, userMsg]);
    setInput("");

    // Simulate Aeon Response (In production, this would call the orchestrator)
    setTimeout(() => {
      const aeonMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "aeon",
        text: "Procesando intención soberana. He mapeado tu comando en el sistema nervioso de KoruOS.",
        emotion: "curiosity",
        timestamp: Date.now()
      };
      setMessages(prev => [...prev, aeonMsg]);
    }, 1500);
  };

  return (
    <div className="flex flex-col h-[500px] bg-white/[0.01] border border-white/5 rounded-[2rem] overflow-hidden backdrop-blur-3xl shadow-2xl">
      <div className="flex-1 overflow-hidden flex flex-col p-4">
        <ConversationFeed messages={messages} />
      </div>
      
      <div className="p-6 bg-black/20 border-t border-white/5 flex gap-4 items-center">
        <div className="relative flex-1">
          <input 
            type="text" 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Escribe un comando o mensaje..."
            className="w-full bg-white/5 border border-white/10 rounded-2xl py-4 px-6 text-sm focus:outline-none focus:border-indigo-500 transition-all pr-12"
          />
          <div className="absolute right-4 top-1/2 -translate-y-1/2 text-indigo-500 opacity-50">
            <Sparkles size={16} />
          </div>
        </div>
        <button 
          onClick={handleSend}
          className="p-4 bg-indigo-500 text-white rounded-2xl hover:bg-indigo-400 transition-all shadow-lg shadow-indigo-500/20"
        >
          <Send size={20} />
        </button>
      </div>
    </div>
  );
}
