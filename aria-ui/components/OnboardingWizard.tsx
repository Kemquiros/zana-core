'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { invoke } from '@tauri-apps/api/core';
import { open } from '@tauri-apps/plugin-dialog';
import { Shield, Key, FolderOpen, ChevronRight, CheckCircle2 } from 'lucide-react';

export default function OnboardingWizard({ onComplete }: { onComplete: () => void }) {
  const [step, setStep] = useState(0);
  const [vaultPath, setVaultPath] = useState('');
  const [keys, setKeys] = useState<Record<string, string>>({
    ANTHROPIC_API_KEY: '',
    OPENAI_API_KEY: '',
    GEMINI_API_KEY: '',
    GROQ_API_KEY: '',
  });
  const [saving, setSaving] = useState(false);

  const steps = [
    {
      title: 'Protocolo de Inicialización',
      desc: 'Bienvenido al Córtex Cognitivo Soberano. ZANA correrá localmente en tu máquina, garantizando privacidad absoluta.',
      icon: <Shield className="w-8 h-8 text-indigo-400" />
    },
    {
      title: 'Bóveda de Conocimiento',
      desc: 'Selecciona la carpeta donde ZANA leerá y escribirá tus recuerdos. (Ej: Tu bóveda de Obsidian).',
      icon: <FolderOpen className="w-8 h-8 text-indigo-400" />
    },
    {
      title: 'Bring Your Own Key (BYOK)',
      desc: 'ZANA procesa tu información de forma segura. Para el razonamiento profundo, puedes conectar tus propias llaves.',
      icon: <Key className="w-8 h-8 text-indigo-400" />
    }
  ];

  const handleSelectVault = async () => {
    try {
      const selected = await open({
        directory: true,
        multiple: false,
        title: 'Selecciona tu Bóveda ZANA'
      });
      if (selected && typeof selected === 'string') {
        setVaultPath(selected);
      }
    } catch (e) {
      console.error('Dialog failed', e);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const config = {
        VAULT_PATH: vaultPath,
        ...Object.fromEntries(Object.entries(keys).filter(([k, v]) => k !== '' && v.trim() !== ''))
      };
      await invoke('save_env_config', { config });
      onComplete();
    } catch (e) {
      console.error('Failed to save config', e);
    } finally {
      setSaving(false);
    }
  };

  const current = steps[step];

  return (
    <div className="min-h-screen bg-black text-white flex flex-col items-center justify-center p-8 relative overflow-hidden">
      <div className="fixed inset-0 bg-[radial-gradient(circle_at_50%_50%,#0a0a1a_0%,#000000_100%)] pointer-events-none" />
      
      <motion.div 
        key={step}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        className="max-w-xl w-full z-10 bg-white/[0.02] border border-white/5 rounded-[2rem] p-10 space-y-8 backdrop-blur-xl shadow-2xl"
      >
        <div className="flex items-center gap-4">
          <div className="p-4 rounded-full bg-indigo-500/10 border border-indigo-500/20">
            {current.icon}
          </div>
          <div>
            <h2 className="text-2xl font-black italic uppercase tracking-tighter">{current.title}</h2>
            <p className="text-gray-400 text-sm mt-1">{current.desc}</p>
          </div>
        </div>

        {/* Step Content */}
        <div className="min-h-[200px] flex flex-col justify-center">
          {step === 0 && (
            <div className="space-y-4 text-center">
              <p className="text-gray-300">ZANA unificará tu memoria semántica, episódica y procedimental en un motor de acero forjado en Rust.</p>
              <p className="text-indigo-400 font-mono text-xs uppercase tracking-widest">Soberanía Absoluta</p>
            </div>
          )}

          {step === 1 && (
            <div className="space-y-6">
              <button 
                onClick={handleSelectVault}
                className="w-full p-6 border border-dashed border-white/20 rounded-2xl hover:border-indigo-500 hover:bg-indigo-500/5 transition-all text-left flex flex-col gap-2"
              >
                <span className="text-sm font-bold text-gray-300">Ruta de la Bóveda</span>
                <span className="text-xs font-mono text-gray-500 break-all">
                  {vaultPath || 'Haz clic para seleccionar carpeta...'}
                </span>
              </button>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              {Object.keys(keys).map((key) => (
                <div key={key}>
                  <label className="block text-[10px] font-mono text-gray-500 uppercase tracking-widest mb-1">{key.replace('_API_KEY', '')}</label>
                  <input 
                    type="password"
                    placeholder="sk-..."
                    className="w-full bg-black/50 border border-white/10 rounded-xl p-3 text-sm focus:outline-none focus:border-indigo-500 transition-all"
                    value={keys[key]}
                    onChange={(e) => setKeys({...keys, [key]: e.target.value})}
                  />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Navigation */}
        <div className="flex justify-between items-center pt-6 border-t border-white/5">
          <div className="flex gap-2">
            {steps.map((_, i) => (
              <div key={i} className={`h-1.5 rounded-full transition-all ${i === step ? 'w-6 bg-indigo-500' : 'w-1.5 bg-white/20'}`} />
            ))}
          </div>
          
          {step < steps.length - 1 ? (
            <button 
              onClick={() => setStep(s => s + 1)}
              className="flex items-center gap-2 px-6 py-3 bg-white text-black rounded-full font-bold text-xs uppercase tracking-widest hover:bg-indigo-500 hover:text-white transition-all"
            >
              Siguiente <ChevronRight className="w-4 h-4" />
            </button>
          ) : (
            <button 
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-2 px-6 py-3 bg-indigo-500 text-white rounded-full font-bold text-xs uppercase tracking-widest hover:bg-indigo-400 transition-all disabled:opacity-50"
            >
              {saving ? 'Forjando...' : 'Completar'} <CheckCircle2 className="w-4 h-4" />
            </button>
          )}
        </div>
      </motion.div>
    </div>
  );
}
