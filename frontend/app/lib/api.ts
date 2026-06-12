import { getIdToken } from "./firebase";
import { ProcessResponse, HistoryPage } from "../types";

const HISTORY_URL = process.env.NEXT_PUBLIC_HISTORY_FUNCTION_URL ?? "";
const UPLOAD_URL = process.env.NEXT_PUBLIC_UPLOAD_FUNCTION_URL ?? "";
const SPEECH_URL = process.env.NEXT_PUBLIC_SPEECH_FUNCTION_URL ?? "";
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

async function apiFetch(url: string, init: RequestInit = {}): Promise<Response> {
  const token = await getIdToken();
  const headers: Record<string, string> = {};
  if (init.headers) {
    const h = new Headers(init.headers);
    h.forEach((v, k) => { headers[k] = v; });
  }
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let finalUrl = url;
  if (typeof window !== "undefined" && window.location.search) {
    const searchParams = new URLSearchParams(window.location.search);
    const view = searchParams.get("view");
    if (view) {
      finalUrl += (url.includes("?") ? "&" : "?") + `view=${encodeURIComponent(view)}`;
    }
  }

  return fetch(finalUrl, { ...init, headers });
}

export async function fetchHistory(pageToken?: string): Promise<HistoryPage> {
  const params = new URLSearchParams({ page_size: "12" });
  if (pageToken) params.set("page_token", pageToken);
  const res = await apiFetch(`${HISTORY_URL}?${params}`);
  if (!res.ok) throw new Error(`History fetch failed: ${res.status}`);
  return res.json();
}

export async function deleteHistoryItem(id: string): Promise<void> {
  const res = await apiFetch(`${HISTORY_URL}?id=${encodeURIComponent(id)}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Delete failed: ${res.status}`);
}

export async function deleteAllHistory(): Promise<void> {
  const res = await apiFetch(`${HISTORY_URL}?deleteAll=true`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Delete all failed: ${res.status}`);
}

export async function uploadImage(
  file: File
): Promise<{ image_url: string; filename: string }> {
  const form = new FormData();
  form.append("file", file);
  const res = await apiFetch(UPLOAD_URL, { method: "POST", body: form });
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
  return res.json();
}

export async function transcribeAudio(
  audioBlob: Blob,
  language: string
): Promise<{ transcript: string; style: string }> {
  const form = new FormData();
  form.append("audio", audioBlob, "recording.webm");
  const res = await apiFetch(`${SPEECH_URL}?action=transcribe&language=${language}`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as { error?: string }).error || `Transcription error ${res.status}`);
  }
  return res.json();
}

export async function generateTts(
  text: string,
  language: string
): Promise<{ audio_base64: string; translated_text: string }> {
  const res = await apiFetch(`${SPEECH_URL}?action=tts`, {
    method: "POST",
    body: JSON.stringify({ text, language }),
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as { error?: string }).error || `TTS error ${res.status}`);
  }
  return res.json();
}

export async function translateText(
  text: string,
  sourceLanguage: string,
  targetLanguage: string
): Promise<{ translated_text: string }> {
  const res = await apiFetch(`${SPEECH_URL}?action=translate`, {
    method: "POST",
    body: JSON.stringify({ text, source_language: sourceLanguage, target_language: targetLanguage }),
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) return { translated_text: text }; // graceful fallback
  return res.json();
}

export async function processImage(
  formData: FormData,
  endpoint: string
): Promise<ProcessResponse> {
  const res = await apiFetch(`${API_URL}${endpoint}`, { method: "POST", body: formData });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail || `Error ${res.status}: ${res.statusText}`);
  }
  return res.json();
}
