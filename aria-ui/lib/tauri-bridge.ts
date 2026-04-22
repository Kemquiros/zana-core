"use client";

// Returns true when running inside Tauri Desktop
export const isTauri = () =>
  typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;

// Lazy-import tauri invoke only in desktop context
export async function tauriInvoke<T>(cmd: string, args?: Record<string, unknown>): Promise<T | null> {
  if (!isTauri()) return null;
  const { invoke } = await import("@tauri-apps/api/core");
  return invoke<T>(cmd, args);
}

export interface GatewayStatus {
  running: boolean;
  port: number;
  url: string;
}

export async function getGatewayStatus(): Promise<GatewayStatus | null> {
  return tauriInvoke<GatewayStatus>("gateway_status");
}

export async function restartGateway(): Promise<void> {
  await tauriInvoke("restart_gateway");
}
