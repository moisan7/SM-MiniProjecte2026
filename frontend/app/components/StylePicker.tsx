"use client";

const STYLES = [
  "Dalí", "Picasso", "Van Gogh", "Monet", "Warhol",
  "Manga", "Boceto", "Graffiti", "Minimalista",
  "Disney", "Cyberpunk", "Tribal", "Caricatura",
  "Gótico", "Puntillismo", "Expresionismo", "Realista",
  "Low Poly", "Steampunk", "Ukiyo-e",
];

interface StylePickerProps {
  value: string;
  onChange: (val: string) => void;
  disabled?: boolean;
}

export default function StylePicker({ value, onChange, disabled }: StylePickerProps) {
  return (
    <div>
      <label htmlFor="style-input" className="block text-sm font-medium text-gray-700 mb-2">
        Instrucciones de Estilo (Texto)
      </label>
      <div className="relative mb-3">
        <input
          id="style-input"
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Ej: Haz un dibujo estilo Dali"
          className="block w-full rounded-lg text-gray-700 border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 p-2 pr-8 border placeholder-gray-500"
          disabled={disabled}
          onKeyDown={(e) => { if (e.key === "Enter") e.preventDefault(); }}
        />
        {value && (
          <button
            type="button"
            onClick={() => onChange("")}
            aria-label="Borrar texto de estilo"
            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 focus:outline-none"
          >
            <svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        )}
      </div>
      <div className="flex flex-wrap gap-2" role="group" aria-label="Estilos rápidos">
        {STYLES.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => onChange(`Estilo ${s}`)}
            aria-label={`Seleccionar estilo ${s}`}
            className="px-2 py-1 text-xs font-medium rounded-full bg-blue-50 text-blue-600 border border-blue-100 hover:bg-blue-100 transition-colors"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
