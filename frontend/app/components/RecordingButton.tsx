"use client";

interface RecordingButtonProps {
  isRecording: boolean;
  audioBlob: Blob | null;
  onStart: () => void;
  onStop: () => void;
  onClear: () => void;
}

export default function RecordingButton({ isRecording, audioBlob, onStart, onStop, onClear }: RecordingButtonProps) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">Comando de Voz</label>
      <div className="flex items-center space-x-3">
        {!isRecording ? (
          <button
            type="button"
            onClick={onStart}
            aria-label="Iniciar grabación de voz"
            className="flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
          >
            🎤 Grabar
          </button>
        ) : (
          <button
            type="button"
            onClick={onStop}
            aria-label="Detener grabación de voz"
            aria-live="polite"
            className="flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-gray-600 animate-pulse focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
          >
            🛑 Grabando… (pulsa para detener)
          </button>
        )}
        {audioBlob && !isRecording && (
          <span className="flex items-center gap-1.5">
            <span className="text-green-600 text-sm font-medium" role="status">✓ Audio grabado</span>
            <button
              type="button"
              onClick={onClear}
              aria-label="Descartar audio grabado"
              className="text-gray-400 hover:text-gray-600 focus:outline-none"
            >
              <svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </button>
          </span>
        )}
      </div>
    </div>
  );
}
