"use client";

import { useEffect } from "react";
import { useTranslations } from "next-intl";
import { motion } from "framer-motion";
import { AlertTriangle, RefreshCw } from "lucide-react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const t = useTranslations("errors");

  useEffect(() => {
    console.error("[ZANA] Runtime error:", error);
  }, [error]);

  return (
    <main className="h-[100dvh] flex flex-col items-center justify-center bg-black font-sans px-6">
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-red-900/10 blur-[100px] rounded-full" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="relative z-10 flex flex-col items-center gap-6 max-w-sm text-center"
      >
        <div className="w-14 h-14 bg-red-950/60 border border-red-800/40 rounded-2xl flex items-center justify-center">
          <AlertTriangle className="w-7 h-7 text-red-400" />
        </div>

        <div className="space-y-2">
          <p className="text-white font-bold tracking-tight">{t("unexpected")}</p>
          {error.digest && (
            <p className="text-slate-600 font-mono text-xs">{error.digest}</p>
          )}
        </div>

        <button
          onClick={reset}
          className="flex items-center gap-2 px-5 py-2.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-sm font-bold text-slate-300 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          {t("retry")}
        </button>
      </motion.div>

      <p className="absolute bottom-4 text-[10px] text-slate-700 font-mono tracking-widest">
        ZANA · ERROR BOUNDARY
      </p>
    </main>
  );
}
