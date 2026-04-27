'use client';

import { Minus, Square, X } from 'lucide-react';
import { useEffect, useState } from 'react';

export default function TitleBar() {
  const [isTauri, setIsTauri] = useState(false);

  useEffect(() => {
    // Only render controls in Tauri environment
    if (typeof window !== 'undefined' && (window as any).__TAURI_INTERNALS__) {
      requestAnimationFrame(() => setIsTauri(true));
    }
  }, []);

  if (!isTauri) return null;

  const minimize = async () => {
    const { getCurrentWindow } = await import('@tauri-apps/api/window');
    await getCurrentWindow().minimize();
  };

  const toggleMaximize = async () => {
    const { getCurrentWindow } = await import('@tauri-apps/api/window');
    await getCurrentWindow().toggleMaximize();
  };

  const close = async () => {
    const { getCurrentWindow } = await import('@tauri-apps/api/window');
    await getCurrentWindow().close();
  };

  return (
    <div data-tauri-drag-region className="fixed top-0 left-0 right-0 h-10 bg-transparent flex justify-end items-center z-[100] px-3 select-none">
      <div className="flex gap-2">
        <button onClick={minimize} className="p-1.5 hover:bg-white/10 rounded-md text-gray-500 hover:text-white transition-colors cursor-default">
          <Minus className="w-3.5 h-3.5" />
        </button>
        <button onClick={toggleMaximize} className="p-1.5 hover:bg-white/10 rounded-md text-gray-500 hover:text-white transition-colors cursor-default">
          <Square className="w-3.5 h-3.5" />
        </button>
        <button onClick={close} className="p-1.5 hover:bg-red-500/20 hover:text-red-500 rounded-md text-gray-500 transition-colors cursor-default">
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
