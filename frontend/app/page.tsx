"use client";

import { useState, useEffect, useRef } from "react";
import { ProcessResponse } from "./types";
import StylePicker from "./components/StylePicker";
import RecordingButton from "./components/RecordingButton";
import ResultPanel from "./components/ResultPanel";
import HistoryPanel from "./components/HistoryPanel";
import ErrorBoundary from "./components/ErrorBoundary";
import { signInAnon } from "./lib/firebase";
import * as api from "./lib/api";

export default function Home() {
  const [uid, setUid] = useState<string | null>(null);
  const [image, setImage] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [styleInput, setStyleInput] = useState("");
  const [advancedMode, setAdvancedMode] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [processing, setProcessing] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [result, setResult] = useState<ProcessResponse | null>(null);
  const [historyItems, setHistoryItems] = useState<ProcessResponse[]>([]);
  const [nextPageToken, setNextPageToken] = useState<string | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [historyError, setHistoryError] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showResult, setShowResult] = useState(true);
  const [showHistory, setShowHistory] = useState(true);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  // Sign in anonymously once on mount — sets uid which gates all API calls
  useEffect(() => {
    signInAnon()
      .then(setUid)
      .catch((err) => {
        setError(`Error de autenticación: ${err?.message ?? err}. Recarga la página.`);
      });
  }, []);

  // Start fetching history and polling once we have a uid
  useEffect(() => {
    if (!uid) return;
    fetchHistory();
    const interval = setInterval(() => fetchHistory(), 20_000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [uid]);

  useEffect(() => {
    return () => { if (previewUrl) URL.revokeObjectURL(previewUrl); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchHistory = async (retries = 3) => {
    setHistoryLoading(true);
    try {
      const page = await api.fetchHistory();
      setHistoryItems(page.items);
      setNextPageToken(page.next_page_token);
      setHistoryError(false);
    } catch {
      if (retries > 0) {
        setTimeout(() => fetchHistory(retries - 1), 2_000);
        return;
      }
      setHistoryError(true);
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleLoadMore = async () => {
    if (!nextPageToken || loadingMore) return;
    setLoadingMore(true);
    try {
      const page = await api.fetchHistory(nextPageToken);
      setHistoryItems(prev => [...prev, ...page.items]);
      setNextPageToken(page.next_page_token);
    } catch {
      // load more failed — user can retry by clicking the button again
    } finally {
      setLoadingMore(false);
    }
  };

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setPreviewUrl(prev => { if (prev) URL.revokeObjectURL(prev); return URL.createObjectURL(file); });
      setImage(file);
      setResult(null);
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      audioChunksRef.current = [];
      recorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunksRef.current.push(e.data); };
      recorder.onstop = () => {
        setAudioBlob(new Blob(audioChunksRef.current, { type: "audio/webm" }));
        stream.getTracks().forEach(t => t.stop());
      };
      recorder.start();
      setIsRecording(true);
      setAudioBlob(null);
    } catch {
      setError("No se pudo acceder al micrófono. Comprueba los permisos del navegador.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const handleReset = () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setImage(null);
    setPreviewUrl(null);
    setResult(null);
    setAudioBlob(null);
    setStyleInput("");
    setError(null);
    const input = document.getElementById("image-input") as HTMLInputElement | null;
    if (input) input.value = "";
  };

  const deleteHistoryItem = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.deleteHistoryItem(id);
      setHistoryItems(prev => prev.filter(h => h.id !== id));
    } catch {
      // deletion failed — history will reconcile on next auto-refresh
    }
  };

  const handleDeleteAll = async () => {
    try {
      await api.deleteAllHistory();
      setHistoryItems([]);
      setNextPageToken(null);
    } catch {
      // failed silently — user can retry
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!image) { setError("Por favor, selecciona una imagen."); return; }

    setProcessing(true);
    setError(null);
    setStatusMessage("Subiendo imagen…");
    const t1 = setTimeout(() => setStatusMessage("Detectando bordes y contornos…"), 800);
    const t2 = setTimeout(() => setStatusMessage("Optimizando trazos para el robot…"), 2500);
    const t3 = setTimeout(() => setStatusMessage("Guardando resultado…"), 5000);

    try {
      const formData = new FormData();
      let endpoint = "/process";
      formData.append("advanced_mode", advancedMode.toString());

      if (audioBlob) {
        endpoint = "/process/voice";
        formData.append("image", image);
        formData.append("audio", audioBlob);
      } else if (styleInput) {
        endpoint = "/process/text";
        formData.append("image", image);
        formData.append("text", styleInput);
      } else {
        formData.append("file", image);
        formData.append("style", "default");
      }

      const data = await api.processImage(formData, endpoint);
      setResult(data);
      setShowResult(true);
      if (data.id) {
        setHistoryItems(prev => [data, ...prev.filter(h => h.id !== data.id)]);
      }
      // Refresh from server after a short delay to confirm persistence
      setTimeout(() => fetchHistory(1), 800);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Ocurrió un error al procesar la imagen.";
      setError(msg);
    } finally {
      clearTimeout(t1); clearTimeout(t2); clearTimeout(t3);
      setProcessing(false);
      setStatusMessage(null);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8 font-sans">
      <div className="max-w-6xl mx-auto">
        <header className="text-center mb-12">
          <h1 className="text-4xl font-extrabold text-gray-900 mb-4">Dal-i Explorer</h1>
          <p className="text-lg text-gray-600">Sistema Robótico de Dibujo Colaborativo 🖼️</p>
        </header>

        <div className="bg-white rounded-2xl shadow-xl p-8 mb-8">
          <form onSubmit={handleSubmit} className="space-y-6" noValidate>
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="flex-1">
                <label htmlFor="image-input" className="block text-sm font-medium text-gray-700 mb-2">
                  Imagen de entrada
                </label>
                <div className="flex items-center gap-3">
                  <input
                    id="image-input"
                    type="file"
                    accept="image/*"
                    onChange={handleImageChange}
                    className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                  />
                  {image && (
                    <button
                      type="button"
                      onClick={handleReset}
                      aria-label="Nueva imagen — limpiar todo"
                      title="Nueva imagen"
                      className="flex-shrink-0 w-9 h-9 flex items-center justify-center rounded-full bg-gray-100 hover:bg-red-100 hover:text-red-600 text-gray-500 transition-colors focus:outline-none focus:ring-2 focus:ring-red-400"
                    >
                      <svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                      </svg>
                    </button>
                  )}
                  {previewUrl && (
                    <img
                      src={previewUrl}
                      alt="Previsualización de imagen seleccionada"
                      className="flex-shrink-0 w-16 h-16 object-cover rounded-lg border-2 border-blue-100 shadow-sm"
                    />
                  )}
                </div>
              </div>
              <div className="flex items-center space-x-3 bg-gray-50 p-3 rounded-xl border border-gray-100">
                <label htmlFor="advanced-mode-toggle" className="text-sm font-semibold text-gray-700">
                  Modo Avanzado (IA Generativa)
                </label>
                <button
                  type="button"
                  id="advanced-mode-toggle"
                  role="switch"
                  aria-checked={advancedMode}
                  aria-label="Activar Modo Avanzado con IA Generativa"
                  onClick={() => setAdvancedMode(v => !v)}
                  className={`${advancedMode ? "bg-blue-600" : "bg-gray-200"} relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2`}
                >
                  <span
                    aria-hidden="true"
                    className={`${advancedMode ? "translate-x-5" : "translate-x-0"} pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out`}
                  />
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr] gap-4 items-start">
              <StylePicker value={styleInput} onChange={setStyleInput} disabled={isRecording} />
              <div className="hidden md:flex flex-col items-center justify-center h-full pt-7 select-none">
                <div className="w-px flex-1 bg-gray-200" />
                <span className="my-2 text-xs font-bold text-gray-400 uppercase tracking-widest">O</span>
                <div className="w-px flex-1 bg-gray-200" />
              </div>
              <RecordingButton
                isRecording={isRecording}
                audioBlob={audioBlob}
                onStart={startRecording}
                onStop={stopRecording}
                onClear={() => setAudioBlob(null)}
              />
            </div>

            <button
              type="submit"
              disabled={processing || !image || !uid}
              className={`w-full flex justify-center py-3 px-4 border border-transparent rounded-xl shadow-sm text-lg font-bold text-white ${processing || !image || !uid ? "bg-gray-400 cursor-not-allowed" : "bg-blue-600 hover:bg-blue-700"} focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors`}
            >
              {processing ? (
                <span className="flex flex-col items-center gap-1" role="status" aria-live="polite">
                  <span className="flex items-center">
                    <svg aria-hidden="true" className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    {statusMessage ?? "Procesando…"}
                  </span>
                </span>
              ) : "🚀 Generar Dibujo"}
            </button>
          </form>

          {error && (
            <div role="alert" className="mt-4 p-4 bg-red-50 text-red-700 rounded-lg border border-red-200">
              {error}
            </div>
          )}
        </div>

        {result && (
          <ErrorBoundary key={result.id ?? result.image_url}>
            <ResultPanel
              result={result}
              show={showResult}
              onToggle={() => setShowResult(v => !v)}
              previewUrl={previewUrl}
            />
          </ErrorBoundary>
        )}

        <HistoryPanel
          history={historyItems}
          loading={historyLoading}
          hasError={historyError}
          onRetry={() => { setHistoryError(false); fetchHistory(); }}
          show={showHistory}
          onToggle={() => setShowHistory(v => !v)}
          onSelect={(item) => { setResult(item); setShowResult(true); }}
          onDelete={deleteHistoryItem}
          onDeleteAll={handleDeleteAll}
          hasMore={nextPageToken !== null}
          onLoadMore={handleLoadMore}
          loadingMore={loadingMore}
        />
      </div>
    </div>
  );
}
