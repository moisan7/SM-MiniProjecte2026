"use client";

import { ProcessResponse } from "../types";

interface HistoryPanelProps {
  history: ProcessResponse[];
  loading: boolean;
  hasError: boolean;
  onRetry: () => void;
  show: boolean;
  onToggle: () => void;
  onSelect: (item: ProcessResponse) => void;
  onDelete: (id: string, e: React.MouseEvent) => void;
}

export default function HistoryPanel({ history, loading, hasError, onRetry, show, onToggle, onSelect, onDelete }: HistoryPanelProps) {
  if (loading) {
    return (
      <div className="mt-12 text-center text-sm text-gray-400 animate-pulse">
        Cargando historial…
      </div>
    );
  }

  if (hasError) {
    return (
      <div className="mt-12 text-center text-sm text-gray-500">
        No se pudo cargar el historial.{" "}
        <button onClick={onRetry} className="underline text-blue-500 hover:text-blue-700">
          Reintentar
        </button>
      </div>
    );
  }

  if (history.length === 0) return null;

  return (
    <div className="mt-12">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={show}
        aria-controls="history-content"
        className="w-full flex items-center justify-between mb-6 group"
      >
        <h2 className="text-2xl font-bold text-gray-900">
          Historial de Generaciones
          <span className="ml-2 text-sm font-normal text-gray-400">({history.length})</span>
        </h2>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
          className={`h-6 w-6 text-gray-400 transition-transform duration-300 ${show ? "rotate-0" : "-rotate-90"}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {show && (
        <div id="history-content" className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {history.map((item, index) => (
            <div
              key={item.id ?? index}
              onClick={() => onSelect(item)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onSelect(item); }}
              aria-label={`Ver resultado de estilo ${item.style}`}
              className="bg-white rounded-xl shadow-md overflow-hidden hover:shadow-lg transition-shadow cursor-pointer border border-gray-100 group relative"
            >
              {item.id && (
                <button
                  onClick={(e) => onDelete(item.id!, e)}
                  aria-label={`Eliminar ${item.style} del historial`}
                  className="absolute top-2 right-2 z-20 bg-red-500 text-white rounded-full p-2 opacity-60 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity hover:bg-red-600 focus:outline-none focus:ring-2 focus:ring-red-500 shadow-lg"
                >
                  <svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                </button>
              )}
              <div className="aspect-video relative overflow-hidden bg-white flex items-center justify-center">
                <img
                  src={item.styled_image_url || item.image_url}
                  alt={`Imagen en estilo ${item.style}`}
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
      )}
    </div>
  );
}
