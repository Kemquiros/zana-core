import { useTranslations } from "next-intl";
import Link from "next/link";
import { Layers } from "lucide-react";

export default function NotFound() {
  const t = useTranslations("errors");

  return (
    <main className="h-[100dvh] flex flex-col items-center justify-center bg-black font-sans px-6">
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-innovation/5 blur-[100px] rounded-full" />
      </div>

      <div className="relative z-10 flex flex-col items-center gap-6 max-w-sm text-center">
        <div className="w-14 h-14 bg-white/5 border border-white/10 rounded-2xl flex items-center justify-center">
          <span className="text-2xl font-black text-slate-500">404</span>
        </div>

        <div className="space-y-1">
          <p className="text-white font-bold tracking-tight">{t("notFound")}</p>
        </div>

        <Link
          href="/"
          className="flex items-center gap-2 px-5 py-2.5 bg-innovation/10 hover:bg-innovation/20 border border-innovation/20 rounded-xl text-sm font-bold text-innovation transition-colors"
        >
          <Layers className="w-4 h-4" />
          {t("notFoundAction")}
        </Link>
      </div>

      <p className="absolute bottom-4 text-[10px] text-slate-700 font-mono tracking-widest">
        ZANA · NODO SENSORIAL
      </p>
    </main>
  );
}
