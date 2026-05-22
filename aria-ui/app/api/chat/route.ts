import { NextRequest } from "next/server";
import fs from "fs";
import path from "path";
import os from "os";

// ─── Types ────────────────────────────────────────────────────────────────────

interface ChatMessage {
  role: string;
  content: string;
}

interface RequestBody {
  messages: ChatMessage[];
}

// ─── Constants ────────────────────────────────────────────────────────────────

const PLACEHOLDER_KEYS = new Set([
  "your_key_here",
  "sk-...",
  "AIza...",
  "gsk_...",
  "sk-ant-...",
  "",
]);

const ZANA_ENV_PATH = path.join(os.homedir(), ".zana", ".env");

// ─── Env parsing ──────────────────────────────────────────────────────────────

function readZanaEnv(): Record<string, string> {
  try {
    const raw = fs.readFileSync(ZANA_ENV_PATH, "utf-8");
    const result: Record<string, string> = {};
    for (const line of raw.split("\n")) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#")) continue;
      const eqIdx = trimmed.indexOf("=");
      if (eqIdx === -1) continue;
      const key = trimmed.slice(0, eqIdx).trim();
      const value = trimmed.slice(eqIdx + 1).trim().replace(/^["']|["']$/g, "");
      if (key) result[key] = value;
    }
    return result;
  } catch {
    return {};
  }
}

function isValidKey(key: string | undefined): key is string {
  if (!key) return false;
  const lower = key.toLowerCase();
  for (const placeholder of PLACEHOLDER_KEYS) {
    if (lower === placeholder.toLowerCase() || key === placeholder) return false;
  }
  return key.length > 10;
}

// ─── Provider detection ───────────────────────────────────────────────────────

type Provider = "anthropic" | "gemini" | "openai" | "groq";

interface ProviderConfig {
  provider: Provider;
  apiKey: string;
  model: string;
}

function detectProvider(env: Record<string, string>): ProviderConfig | null {
  const anthropicKey = env["ANTHROPIC_API_KEY"];
  if (isValidKey(anthropicKey)) {
    return { provider: "anthropic", apiKey: anthropicKey, model: "claude-3-5-haiku-20241022" };
  }

  const geminiKey = env["GEMINI_API_KEY"];
  if (isValidKey(geminiKey)) {
    return { provider: "gemini", apiKey: geminiKey, model: "gemini-2.0-flash" };
  }

  const openaiKey = env["OPENAI_API_KEY"];
  if (isValidKey(openaiKey)) {
    return { provider: "openai", apiKey: openaiKey, model: "gpt-4o-mini" };
  }

  const groqKey = env["GROQ_API_KEY"];
  if (isValidKey(groqKey)) {
    return { provider: "groq", apiKey: groqKey, model: "llama-3.3-70b-versatile" };
  }

  return null;
}

// ─── SSE helpers ──────────────────────────────────────────────────────────────

const encoder = new TextEncoder();

function sseChunk(delta: string): Uint8Array {
  return encoder.encode(`data: ${JSON.stringify({ delta })}\n\n`);
}

function sseDone(): Uint8Array {
  return encoder.encode("data: [DONE]\n\n");
}

function sseError(message: string): Uint8Array {
  return encoder.encode(`data: ${JSON.stringify({ error: message })}\n\n`);
}

// ─── Provider streaming functions ────────────────────────────────────────────

async function streamAnthropic(
  config: ProviderConfig,
  messages: ChatMessage[],
  controller: ReadableStreamDefaultController<Uint8Array>,
): Promise<void> {
  const response = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": config.apiKey,
      "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify({
      model: config.model,
      max_tokens: 1024,
      stream: true,
      messages: messages.map((m) => ({
        role: m.role === "aeon" ? "assistant" : m.role === "user" ? "user" : "user",
        content: m.content,
      })),
    }),
  });

  if (!response.ok || !response.body) {
    controller.enqueue(sseError(`Anthropic error: ${response.status}`));
    return;
  }

  const reader = response.body.getReader();
  const dec = new TextDecoder();
  let buf = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const lines = buf.split("\n");
    buf = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const payload = line.slice(6).trim();
      if (payload === "[DONE]") return;
      try {
        const parsed = JSON.parse(payload) as {
          type: string;
          delta?: { type: string; text?: string };
        };
        if (parsed.type === "content_block_delta" && parsed.delta?.text) {
          controller.enqueue(sseChunk(parsed.delta.text));
        }
      } catch {
        /* skip malformed lines */
      }
    }
  }
}

async function streamGemini(
  config: ProviderConfig,
  messages: ChatMessage[],
  controller: ReadableStreamDefaultController<Uint8Array>,
): Promise<void> {
  const contents = messages.map((m) => ({
    role: m.role === "aeon" ? "model" : "user",
    parts: [{ text: m.content }],
  }));

  const url = `https://generativelanguage.googleapis.com/v1beta/models/${config.model}:streamGenerateContent?alt=sse&key=${config.apiKey}`;

  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ contents }),
  });

  if (!response.ok || !response.body) {
    controller.enqueue(sseError(`Gemini error: ${response.status}`));
    return;
  }

  const reader = response.body.getReader();
  const dec = new TextDecoder();
  let buf = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const lines = buf.split("\n");
    buf = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const payload = line.slice(6).trim();
      if (payload === "[DONE]") return;
      try {
        const parsed = JSON.parse(payload) as {
          candidates?: Array<{ content?: { parts?: Array<{ text?: string }> } }>;
        };
        const text = parsed.candidates?.[0]?.content?.parts?.[0]?.text;
        if (text) controller.enqueue(sseChunk(text));
      } catch {
        /* skip malformed lines */
      }
    }
  }
}

async function streamOpenAI(
  config: ProviderConfig,
  messages: ChatMessage[],
  controller: ReadableStreamDefaultController<Uint8Array>,
  baseUrl = "https://api.openai.com/v1",
): Promise<void> {
  const response = await fetch(`${baseUrl}/chat/completions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${config.apiKey}`,
    },
    body: JSON.stringify({
      model: config.model,
      stream: true,
      messages: messages.map((m) => ({
        role: m.role === "aeon" ? "assistant" : m.role === "user" ? "user" : "system",
        content: m.content,
      })),
    }),
  });

  if (!response.ok || !response.body) {
    controller.enqueue(sseError(`${config.provider} error: ${response.status}`));
    return;
  }

  const reader = response.body.getReader();
  const dec = new TextDecoder();
  let buf = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const lines = buf.split("\n");
    buf = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const payload = line.slice(6).trim();
      if (payload === "[DONE]") return;
      try {
        const parsed = JSON.parse(payload) as {
          choices?: Array<{ delta?: { content?: string } }>;
        };
        const content = parsed.choices?.[0]?.delta?.content;
        if (content) controller.enqueue(sseChunk(content));
      } catch {
        /* skip malformed lines */
      }
    }
  }
}

// ─── Route Handler ────────────────────────────────────────────────────────────

export async function POST(req: NextRequest): Promise<Response> {
  let body: RequestBody;
  try {
    body = (await req.json()) as RequestBody;
  } catch {
    return new Response(JSON.stringify({ error: "invalid_body" }), { status: 400 });
  }

  const env = readZanaEnv();
  const providerConfig = detectProvider(env);

  // Probe request (empty messages array) — just report availability
  if (!body.messages || body.messages.length === 0) {
    if (!providerConfig) {
      return new Response(JSON.stringify({ error: "no_provider" }), {
        status: 503,
        headers: { "Content-Type": "application/json" },
      });
    }
    return new Response(JSON.stringify({ provider: providerConfig.provider }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }

  if (!providerConfig) {
    return new Response(JSON.stringify({ error: "no_provider" }), {
      status: 503,
      headers: { "Content-Type": "application/json" },
    });
  }

  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      try {
        switch (providerConfig.provider) {
          case "anthropic":
            await streamAnthropic(providerConfig, body.messages, controller);
            break;
          case "gemini":
            await streamGemini(providerConfig, body.messages, controller);
            break;
          case "openai":
            await streamOpenAI(providerConfig, body.messages, controller);
            break;
          case "groq":
            await streamOpenAI(
              { ...providerConfig },
              body.messages,
              controller,
              "https://api.groq.com/openai/v1",
            );
            break;
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : "stream_error";
        controller.enqueue(sseError(msg));
      } finally {
        controller.enqueue(sseDone());
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
