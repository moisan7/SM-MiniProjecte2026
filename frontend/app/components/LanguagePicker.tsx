"use client";

interface LanguagePickerProps {
  value: string;
  onChange: (lang: string) => void;
  disabled?: boolean;
}

export const SUPPORTED_LANGUAGES: Record<string, string> = {
  "es-ES": "Español",
  "en-US": "English",
  "fr-FR": "Français",
  "de-DE": "Deutsch",
  "it-IT": "Italiano",
  "pt-BR": "Português",
  "ca-ES": "Català",
  "ja-JP": "日本語",
  "zh-CN": "中文",
  "ar-XA": "العربية",
};

export default function LanguagePicker({ value, onChange, disabled }: LanguagePickerProps) {
  return (
    <div className="flex items-center gap-2">
      <label htmlFor="language-picker" className="text-sm font-medium text-gray-700 whitespace-nowrap">
        Idioma / Language
      </label>
      <select
        id="language-picker"
        value={value}
        onChange={e => onChange(e.target.value)}
        disabled={disabled}
        className="text-sm border border-gray-200 rounded-lg px-2 py-1.5 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {Object.entries(SUPPORTED_LANGUAGES).map(([code, name]) => (
          <option key={code} value={code}>{name}</option>
        ))}
      </select>
    </div>
  );
}
