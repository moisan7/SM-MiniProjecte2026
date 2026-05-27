"use client";

import { useState, useRef, useEffect } from "react";

interface Coordinate {
  x: number;
  y: number;
}

interface ProcessResponse {
  status: string;
  style: string;
  coordinates: Coordinate[];
  image_url: string;
  styled_image_url?: string;
  transcript?: string;
  message: string;
  audio_base64?: string;
  svg?: string;
  dimensions?: { width: number; height: number };
  id?: string;
}

export default function Home() {
  const [image, setImage] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [styleInput, setStyleInput] = useState("");
  const [advancedMode, setAdvancedMode] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState<ProcessResponse | null>(null);
  const [history, setHistory] = useState<ProcessResponse[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showResult, setShowResult] = useState(true);
  const [showHistory, setShowHistory] = useState(true);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? ""; // Served by same origin in production

  const deleteHistoryItem = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation(); // Evitar que se seleccione el item al borrarlo
    if (!confirm("¿Estás seguro de que quieres eliminar este elemento del historial?")) return;
    
    try {
      const response = await fetch(`${API_BASE_URL}/history/${id}`, {
        method: "DELETE",
      });
      if (response.ok) {
        fetchHistory();
      }
    } catch (err) {
      console.error("Error deleting history item:", err);
    }
  };

  const fetchHistory = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/history`);
      if (response.ok) {
        const data = await response.json();
        setHistory(data);
      }
    } catch (err) {
      console.error("Error fetching history:", err);
    }
  };

  useEffect(() => {
    fetchHistory();
    // Auto-refresh history every 20 s so teammates' submissions appear
    const interval = setInterval(fetchHistory, 20_000);
    return () => clearInterval(interval);
  }, []);

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setImage(file);
      setPreviewUrl(URL.createObjectURL(file));
      setResult(null);
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: "audio/wav" });
        setAudioBlob(blob);
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      setAudioBlob(null);
    } catch (err) {
      console.error("Error accessing microphone:", err);
      setError("No se pudo acceder al micrófono.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!image) {
      setError("Por favor, selecciona una imagen.");
      return;
    }

    setProcessing(true);
    setError(null);

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

      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Error en el servidor: ${response.statusText}`);
      }

      const data: ProcessResponse = await response.json();
      setResult(data);
      setShowResult(true); // always expand result panel when new result arrives
      // Optimistically prepend the new item to history so it appears immediately,
      // then do a real fetch after a short delay to get the server-assigned ID if
      // it wasn't returned (and to sync any concurrent submissions from teammates).
      if (data.id) {
        setHistory(prev => [data, ...prev.filter(h => h.id !== data.id)]);
      }
      setTimeout(fetchHistory, 800);
    } catch (err: any) {
      setError(err.message || "Ocurrió un error al procesar la imagen.");
    } finally {
      setProcessing(false);
    }
  };

  useEffect(() => {
    if (result && canvasRef.current && (previewUrl || result.image_url || result.styled_image_url)) {
      const canvas = canvasRef.current;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      const img = new Image();
      // Prioritize styled image for background if available
      img.src = result.styled_image_url || previewUrl || result.image_url;

      img.onload = () => {
        canvas.width = img.width;
        canvas.height = img.height;
        ctx.drawImage(img, 0, 0);

        // Draw coordinates
        if (result.coordinates.length > 0) {
          ctx.strokeStyle = "red";
          ctx.lineWidth = 2;
          ctx.beginPath();
          
          result.coordinates.forEach((coord, index) => {
            if (index === 0) {
              ctx.moveTo(coord.x, coord.y);
            } else {
              ctx.lineTo(coord.x, coord.y);
            }
          });
          
          ctx.stroke();
        }
      };
    }
  }, [result, previewUrl]);

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8 font-sans">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-extrabold text-gray-900 mb-4">Dal-i Explorer</h1>
          <p className="text-lg text-gray-600">Sistema Robótico de Dibujo Colaborativo 🖼️</p>
        </div>

        <div className="bg-white rounded-2xl shadow-xl p-8 mb-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-2">Imagen de entrada</label>
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleImageChange}
                  className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                />
              </div>
              <div className="flex items-center space-x-3 bg-gray-50 p-3 rounded-xl border border-gray-100">
                <label htmlFor="advanced-mode" className="text-sm font-semibold text-gray-700">
                  Modo Avanzado (IA Generativa)
                </label>
                <button
                  type="button"
                  id="advanced-mode"
                  onClick={() => setAdvancedMode(!advancedMode)}
                  className={`${
                    advancedMode ? "bg-blue-600" : "bg-gray-200"
                  } relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none`}
                >
                  <span
                    aria-hidden="true"
                    className={`${
                      advancedMode ? "translate-x-5" : "translate-x-0"
                    } pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out`}
                  />
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Instrucciones de Estilo (Texto)</label>
                <input
                  type="text"
                  value={styleInput}
                  onChange={(e) => setStyleInput(e.target.value)}
                  placeholder="Ej: Haz un dibujo estilo Dali"
                  className="block w-full rounded-lg text-gray-700 border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 p-2 border placeholder-gray-500 mb-3"
                  disabled={isRecording}
                  onKeyDown={(e) => { if (e.key === "Enter") e.preventDefault(); }}
                />
                <div className="flex flex-wrap gap-2">
                  {[
                    "Dalí", "Picasso", "Van Gogh", "Monet", "Warhol", 
                    "Manga", "Boceto", "Graffiti", "Minimalista", 
                    "Disney", "Cyberpunk", "Tribal", "Caricatura",
                    "Gótico", "Puntillismo", "Expresionismo", "Realista",
                    "Low Poly", "Steampunk", "Ukiyo-e"
                  ].map((s) => (
                    <button
                      key={s}
                      type="button"
                      onClick={() => setStyleInput(`Estilo ${s}`)}
                      className="px-2 py-1 text-xs font-medium rounded-full bg-blue-50 text-blue-600 border border-blue-100 hover:bg-blue-100 transition-colors"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Comando de Voz</label>
                <div className="flex items-center space-x-3">
                  {!isRecording ? (
                    <button
                      type="button"
                      onClick={startRecording}
                      className="flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none"
                    >
                      🎤 Grabar
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={stopRecording}
                      className="flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-gray-600 animate-pulse"
                    >
                      🛑 Detener
                    </button>
                  )}
                  {audioBlob && <span className="text-green-600 text-sm font-medium">✓ Audio grabado</span>}
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={processing || !image}
              className={`w-full flex justify-center py-3 px-4 border border-transparent rounded-xl shadow-sm text-lg font-bold text-white ${
                processing || !image ? "bg-gray-400 cursor-not-allowed" : "bg-blue-600 hover:bg-blue-700"
              } focus:outline-none transition-colors`}
            >
              {processing ? (
                <span className="flex items-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Procesando con IA...
                </span>
              ) : "🚀 Generar Dibujo"}
            </button>
          </form>

          {error && (
            <div className="mt-4 p-4 bg-red-50 text-red-700 rounded-lg border border-red-200">
              {error}
            </div>
          )}
        </div>

        {result && (
          <div className="bg-white rounded-2xl shadow-xl p-8 animate-fade-in">
            {/* Collapsible header */}
            <button
              type="button"
              onClick={() => setShowResult(v => !v)}
              className="w-full flex items-center justify-between group mb-2"
            >
              <div className="flex items-center gap-3">
                <h2 className="text-3xl font-bold text-gray-900">Resultado de Generación</h2>
                <div className="flex items-center gap-2">
                  <span className="px-3 py-1 bg-blue-100 text-blue-700 text-sm font-bold rounded-full capitalize">{result.style}</span>
                  {result.styled_image_url && <span className="px-3 py-1 bg-green-100 text-green-700 text-sm font-bold rounded-full">✨ IA Avanzada</span>}
                </div>
              </div>
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className={`h-6 w-6 text-gray-400 transition-transform duration-300 ${showResult ? "rotate-0" : "-rotate-90"}`}
                fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            <div className={`space-y-12 mt-6 ${showResult ? "" : "hidden"}`}>

            {/* Main Comparison Section */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div className="space-y-4">
                <div className="flex justify-between items-end">
                  <h3 className="text-lg font-bold text-gray-700">Imagen Original</h3>
                  <span className="text-xs text-gray-400 font-medium">Entrada de usuario</span>
                </div>
                <div className="aspect-square relative border-4 border-gray-100 rounded-2xl overflow-hidden bg-gray-50 shadow-inner group">
                  <img src={result.image_url} alt="Original" className="w-full h-full object-contain" />
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex justify-between items-end">
                  <h3 className="text-lg font-bold text-blue-700">Transformación de Estilo</h3>
                  <span className="text-xs text-blue-400 font-medium">Generado por Gemini</span>
                </div>
                <div className="aspect-square relative border-4 border-blue-50 rounded-2xl overflow-hidden bg-gray-50 shadow-inner group">
                  <img 
                    src={result.styled_image_url || result.image_url} 
                    alt="Styled" 
                    className="w-full h-full object-contain" 
                  />
                  {!result.styled_image_url && (
                    <div className="absolute inset-0 flex items-center justify-center bg-gray-100/50 backdrop-blur-sm">
                      <p className="text-sm text-gray-500 font-medium italic text-center px-6">
                        Usa el "Modo Avanzado" para ver la transformación visual aquí
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Description and Stats */}
            <div className="bg-gray-50 rounded-2xl p-6 border border-gray-100">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div className="lg:col-span-2 space-y-4">
                  {result.transcript && (
                    <div>
                      <h4 className="text-xs font-bold text-red-400 uppercase tracking-widest mb-1">Lo que entendí (Voz)</h4>
                      <p className="text-xl font-bold text-gray-800">"{result.transcript}"</p>
                    </div>
                  )}
                  <div>
                    {/* --- MODIFICAMOS ESTA CABECERA PARA METER EL BOTÓN --- */}
                    <div className="flex items-center space-x-3 mb-3">
                      <h4 className="text-sm font-bold text-gray-400 uppercase tracking-widest">Interpretación Artística</h4>
                      
                      {result.audio_base64 && (
                        <button
                          type="button"
                          onClick={() => {
                            const audio = new Audio("data:audio/mp3;base64," + result.audio_base64);
                            audio.play().catch(e => console.error("Error al reproducir el audio:", e));
                          }}
                          className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-bold rounded-lg bg-blue-600 text-white hover:bg-blue-700 active:scale-95 transition-all shadow-sm cursor-pointer"
                        >
                          🔊 Escuchar voz
                        </button>
                      )}
                    </div>
                    {/* ----------------------------------------------------- */}
                    
                    <p className="text-gray-700 italic leading-relaxed text-lg">"{result.message}"</p>
                  </div>
                </div>
                <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-100 flex flex-col justify-center">
                  <h4 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-2">Métricas del Robot</h4>
                  <div className="flex items-baseline space-x-2">
                    <span className="text-3xl font-black text-blue-600">{result.coordinates.length}</span>
                    <span className="text-sm text-gray-500 font-medium">trazos generados</span>
                  </div>
                  <p className="text-[10px] text-gray-400 mt-2">Optimizado para plotter de precisión</p>
                </div>
              </div>
            </div>
            {/* Technical Previews */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 pt-4">
              <div className="space-y-4">
                <h3 className="text-sm font-bold text-gray-500 text-center uppercase tracking-widest">Previsualización de Trazos</h3>
                <div className="border-4 border-gray-100 rounded-xl overflow-hidden shadow-inner bg-gray-900 flex items-center justify-center p-2">
                  <canvas ref={canvasRef} className="max-w-full h-auto rounded-lg shadow-2xl" />
                </div>
              </div>

              {result.svg && (
                <div className="space-y-4">
                  <h3 className="text-sm font-bold text-gray-500 text-center uppercase tracking-widest">Salida Vectorial (SVG)</h3>
                  <div
                    className="border-4 border-blue-50 rounded-xl overflow-hidden shadow-inner bg-white p-4 flex items-center justify-center min-h-[300px]"
                    dangerouslySetInnerHTML={{ __html: result.svg }}
                  />
                </div>
              )}
            </div>
            </div>
          </div>
        )}

        {history.length > 0 && (
          <div className="mt-12">
            {/* Collapsible header */}
            <button
              type="button"
              onClick={() => setShowHistory(v => !v)}
              className="w-full flex items-center justify-between mb-6 group"
            >
              <h2 className="text-2xl font-bold text-gray-900">
                Historial de Generaciones
                <span className="ml-2 text-sm font-normal text-gray-400">({history.length})</span>
              </h2>
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className={`h-6 w-6 text-gray-400 transition-transform duration-300 ${showHistory ? "rotate-0" : "-rotate-90"}`}
                fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            {showHistory && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {history.map((item, index) => (
                <div 
                  key={index} 
                  onClick={() => { setResult(item); setShowResult(true); }}
                  className="bg-white rounded-xl shadow-md overflow-hidden hover:shadow-lg transition-shadow cursor-pointer border border-gray-100 group relative"
                >
                  {item.id && (
                    <button
                      onClick={(e) => deleteHistoryItem(item.id!, e)}
                      className="absolute top-2 right-2 z-20 bg-red-500 text-white rounded-full p-2 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-600 focus:outline-none shadow-lg"
                      title="Eliminar del historial"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                      </svg>
                    </button>
                  )}
                  <div className="aspect-video relative overflow-hidden bg-white flex items-center justify-center">
                      <img 
                        src={item.styled_image_url || item.image_url} 
                        alt={item.style} 
                        className="object-cover w-full h-full group-hover:scale-105 transition-transform duration-300"
                      />
                      {item.styled_image_url && (
                        <div className="absolute bottom-2 right-2 bg-blue-600 text-white text-[10px] font-bold px-2 py-0.5 rounded-full shadow-md">
                          IA
                        </div>
                      )}
                  </div>
                  <div className="p-4">
                    <p className="text-xs font-bold text-blue-600 uppercase tracking-wider mb-1">{item.style}</p>
                    <p className="text-sm text-gray-600 line-clamp-2 italic">"{item.message}"</p>
                  </div>
                </div>
              ))}
            </div>
            )} {/* end showHistory */}
          </div>
        )}
      </div>
    </div>
  );
}
