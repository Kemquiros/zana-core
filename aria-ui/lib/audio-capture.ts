"use client";

import { useRef, useState, useCallback } from "react";

function encodeWav(samples: Float32Array, sampleRate: number): ArrayBuffer {
  const len = samples.length;
  const buf = new ArrayBuffer(44 + len * 2);
  const view = new DataView(buf);

  const writeStr = (off: number, s: string) => {
    for (let i = 0; i < s.length; i++) view.setUint8(off + i, s.charCodeAt(i));
  };

  writeStr(0, "RIFF");
  view.setUint32(4, 36 + len * 2, true);
  writeStr(8, "WAVE");
  writeStr(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);       // PCM
  view.setUint16(22, 1, true);       // mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeStr(36, "data");
  view.setUint32(40, len * 2, true);

  let off = 44;
  for (let i = 0; i < len; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(off, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    off += 2;
  }
  return buf;
}

function bufToBase64(buf: ArrayBuffer): string {
  const bytes = new Uint8Array(buf);
  let bin = "";
  for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
  return btoa(bin);
}

export function useAudioCapture(onCapture: (wavB64: string) => void) {
  const [recording, setRecording] = useState(false);
  const audioCtx = useRef<AudioContext | null>(null);
  const processor = useRef<ScriptProcessorNode | null>(null);
  const source = useRef<MediaStreamAudioSourceNode | null>(null);
  const chunks = useRef<Float32Array[]>([]);
  const stream = useRef<MediaStream | null>(null);

  const startRecording = useCallback(async () => {
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioCtx.current = new AudioContext({ sampleRate: 16000 });
      source.current = audioCtx.current.createMediaStreamSource(stream.current);
      processor.current = audioCtx.current.createScriptProcessor(4096, 1, 1);
      chunks.current = [];

      processor.current.onaudioprocess = (e) => {
        chunks.current.push(new Float32Array(e.inputBuffer.getChannelData(0)));
      };

      source.current.connect(processor.current);
      processor.current.connect(audioCtx.current.destination);
      setRecording(true);
    } catch {
      console.error("No se pudo acceder al micrófono");
    }
  }, []);

  const stopRecording = useCallback(() => {
    if (!audioCtx.current) return;

    processor.current?.disconnect();
    source.current?.disconnect();
    stream.current?.getTracks().forEach((t) => t.stop());

    const totalLen = chunks.current.reduce((s, c) => s + c.length, 0);
    const merged = new Float32Array(totalLen);
    let offset = 0;
    for (const chunk of chunks.current) {
      merged.set(chunk, offset);
      offset += chunk.length;
    }

    const wavBuf = encodeWav(merged, audioCtx.current.sampleRate);
    const b64 = bufToBase64(wavBuf);
    onCapture(b64);

    audioCtx.current.close();
    audioCtx.current = null;
    setRecording(false);
  }, [onCapture]);

  const toggle = useCallback(() => {
    if (recording) stopRecording();
    else startRecording();
  }, [recording, startRecording, stopRecording]);

  return { recording, toggle, startRecording, stopRecording };
}
