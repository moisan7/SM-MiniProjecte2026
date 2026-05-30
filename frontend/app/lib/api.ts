import { getIdToken } from "./firebase";
import { ProcessResponse, HistoryPage } from "../types";

const HISTORY_URL = process.env.NEXT_PUBLIC_HISTORY_FUNCTION_URL ?? "";
const UPLOAD_URL = process.env.NEXT_PUBLIC_UPLOAD_FUNCTION_URL ?? "";
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

async function apiFetch(url: string, init: RequestInit = {}): Promise<Response> {
  const token = await getIdToken();
  const headers: Record<string, string> = {};
  // Copy any existing headers (but skip Content-Type for FormData — browser sets it)
  if (init.headers) {
    const h = new Headers(init.headers);
    h.forEach((v, k) => { headers[k] = v; });
  }
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return fetch(url, { ...init, headers });
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
