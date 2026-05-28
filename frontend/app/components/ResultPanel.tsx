"use client";

import { useRef, useEffect } from "react";
import { ProcessResponse } from "../types";

interface ResultPanelProps {
  result: ProcessResponse;
  show: boolean;
  onToggle: () => void;
  previewUrl: string | null;
}

export default function ResultPanel({ result, show, onToggle, previewUrl }: ResultPanelProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const src = result.styled_image_url || previewUrl || result.image_url;
    if (!src) return;

    const img = new Image();
    img.src = src;

    img.onload = () => {
      canvas.width = img.width;
      canvas.height = img.height;
      ctx.drawImage(img, 0, 0);

      const coords = result.coordinates ?? [];
      if (coords.length > 0) {
        ctx.strokeStyle = "red";
        ctx.lineWidth = 2;
        ctx.beginPath();
        coords.forEach((coord, i) => {
          if (i === 0) ctx.moveTo(coord.x, coord.y);
          else ctx.lineTo(coord.x, coord.y);
        });
        ctx.stroke();
      }
    };
  }, [result, previewUrl]);

  return (
    <div className="bg-white rounded-2xl shadow-xl p-8 animate-fade-in">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={show}
        aria-controls="result-content"
        className="w-full flex items-center justify-between group mb-2"
      >
        <div className="flex items-center gap-3">
          <h2 className="text-3xl font-bold text-gray-900">Resultado de Generación</h2>
          <div className="flex items-center gap-2">
            <span className="px-3 py-1 bg-blue-100 text-blue-700 text-sm font-bold rounded-full capitalize">
              {result.style}
            </span>
            {result.styled_image_url && (
              <span className="px-3 py-1 bg-green-100 text-green-700 text-sm font-bold rounded-full">
                ✨ IA Avanzada
              </span>
            )}
          </div>
        </div>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
          className={`h-6 w-6 text-gray-400 transition-transform duration-300 ${show ? "rotate-0" : "-rotate-90"}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {result.warning && (
        <div role="alert" className="mt-3 p-3 bg-amber-50 text-amber-800 rounded-lg border border-amber-200 text-sm">
          ⚠️ {result.warning}
        </div>
      )}

      <div id="result-content" className={`space-y-12 mt-6 ${show ? "" : "hidden"}`}>
        {/* Image comparison */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="space-y-4">
            <div className="flex justify-between items-end">
              <h3 className="text-lg font-bold text-gray-700">Imagen Original</h3>
              <span className="text-xs text-gray-400 font-medium">Entrada de usuario</span>
            </div>
            <div className="aspect-square relative border-4 border-gray-100 rounded-2xl overflow-hidden bg-gray-50 shadow-inner">
              <img src={result.image_url} alt="Imagen original subida por el usuario" className="w-full h-full object-contain" />
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex justify-between items-end">
              <h3 className="text-lg font-bold text-blue-700">Transformación de Estilo</h3>
              <span className="text-xs text-blue-400 font-medium">Generado por Gemini</span>
            </div>
            <div className="aspect-square relative border-4 border-blue-50 rounded-2xl overflow-hidden bg-gray-50 shadow-inner">
              <img
                src={result.styled_image_url || result.image_url}
                alt={result.styled_image_url ? `Imagen transformada al estilo ${result.style}` : "Sin transformación de estilo"}
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
                <div className="flex items-center space-x-3 mb-3">
                  <h4 className="text-sm font-bold text-gray-400 uppercase tracking-widest">Interpretación Artística</h4>
                  {result.audio_base64 && (
                    <button
                      type="button"
                      aria-label="Reproducir respuesta de voz"
                      onClick={() => {
                        const audio = new Audio("data:audio/mp3;base64," + result.audio_base64);
                        audio.play().catch((e) => console.error("Error al reproducir el audio:", e));
                      }}
                      className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-bold rounded-lg bg-blue-600 text-white hover:bg-blue-700 active:scale-95 transition-all shadow-sm cursor-pointer"
                    >
                      🔊 Escuchar voz
                    </button>
                  )}
                </div>
                <p className="text-gray-700 italic leading-relaxed text-lg">"{result.message}"</p>
              </div>
            </div>
            <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-100 flex flex-col justify-center">
              <h4 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-2">Métricas del Robot</h4>
              <div className="flex items-baseline space-x-2">
                <span className="text-3xl font-black text-blue-600">{result.coordinates?.length ?? 0}</span>
                <span className="text-sm text-gray-500 font-medium">trazos generados</span>
              </div>
              <p className="text-[10px] text-gray-400 mt-2">Optimizado para plotter de precisión</p>
            </div>
          </div>
        </div>

        {/* Technical previews */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 pt-4">
          <div className="space-y-4">
            <h3 className="text-sm font-bold text-gray-500 text-center uppercase tracking-widest">
              Previsualización de Trazos
            </h3>
            <div className="border-4 border-gray-100 rounded-xl overflow-hidden shadow-inner bg-gray-900 flex items-center justify-center p-2">
              <canvas ref={canvasRef} className="max-w-full h-auto rounded-lg shadow-2xl" aria-label="Trazos del robot sobre la imagen" />
            </div>
          </div>

          {result.svg && (
            <div className="space-y-4">
              <h3 className="text-sm font-bold text-gray-500 text-center uppercase tracking-widest">
                Salida Vectorial (SVG)
              </h3>
              <div
                className="border-4 border-blue-50 rounded-xl overflow-hidden shadow-inner bg-white p-4 flex items-center justify-center min-h-[300px]"
                dangerouslySetInnerHTML={{ __html: result.svg }}
                aria-label="Salida vectorial SVG"
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
