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
  message: string;
}

export default function Home() {
  const [image, setImage] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [styleInput, setStyleInput] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState<ProcessResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const API_BASE_URL = ""; // Served by same origin in production

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

      if (audioBlob) {
        endpoint = "/process/voice";
        formData.append("image", image);
        formData.append("audio", audioBlob);
      } else if (styleInput) {
        endpoint = "/process/text"; // We will create this
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
    } catch (err: any) {
      setError(err.message || "Ocurrió un error al procesar la imagen.");
    } finally {
      setProcessing(false);
    }
  };

  useEffect(() => {
    if (result && canvasRef.current && (previewUrl || result.image_url)) {
      const canvas = canvasRef.current;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      const img = new Image();
      img.crossOrigin = "anonymous";
      img.src = result.image_url;

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
          <p className="text-lg text-gray-600">Sistema Robótico de Dibujo Colaborativo</p>
        </div>

        <div className="bg-white rounded-2xl shadow-xl p-8 mb-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Imagen de entrada</label>
              <input
                type="file"
                accept="image/*"
                onChange={handleImageChange}
                className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Instrucciones de Estilo (Texto)</label>
                <input
                  type="text"
                  value={styleInput}
                  onChange={(e) => setStyleInput(e.target.value)}
                  placeholder="Ej: Haz un dibujo estilo Dali"
                  className="block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 p-2 border"
                  disabled={isRecording}
                />
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
              {processing ? "Procesando..." : "🚀 Generar Dibujo"}
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
            <h2 className="text-2xl font-bold text-gray-900 mb-6">Resultado</h2>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <div>
                <p className="text-sm font-medium text-gray-500 mb-1">Estilo detectado:</p>
                <p className="text-lg font-bold text-blue-600 capitalize mb-4">{result.style}</p>
                <p className="text-sm font-medium text-gray-500 mb-1">Mensaje:</p>
                <p className="text-gray-700 italic mb-6">{result.message}</p>
                
                <div className="bg-gray-50 p-4 rounded-lg">
                  <p className="text-xs text-gray-400 uppercase tracking-wider font-bold mb-2">Info Técnica</p>
                  <p className="text-sm text-gray-600">Puntos generados: {result.coordinates.length}</p>
                </div>
              </div>
              
              <div className="flex flex-col items-center">
                <p className="text-sm font-medium text-gray-700 mb-2">Visualización del Plotter</p>
                <div className="border-4 border-gray-100 rounded-xl overflow-hidden shadow-inner bg-gray-50">
                  <canvas ref={canvasRef} className="max-w-full h-auto" />
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
