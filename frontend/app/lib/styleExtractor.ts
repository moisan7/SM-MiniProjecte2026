export const SUPPORTED_STYLES = [
  "picasso", "van gogh", "monet", "dali", "dalí",
  "warhol", "rembrandt", "matisse", "kandinsky",
  "manga", "boceto", "graffiti", "minimalista",
  "disney", "cyberpunk", "tribal", "caricatura",
  "gótico", "gotico", "puntillismo", "expresionismo",
  "realista", "low poly", "steampunk", "ukiyo-e",
] as const;

const _ES_MARKERS = new Set("áéíóúüñ¿¡".split(""));
const _ES_WORDS = new Set(["estilo", "como", "haz", "dibuja", "quiero", "una", "imagen", "con", "para", "que"]);

export function detectLanguage(text: string): "es-ES" | "en-US" {
  const lower = text.toLowerCase();
  if ([...lower].some(c => _ES_MARKERS.has(c))) return "es-ES";
  if (lower.split(/\s+/).some(w => _ES_WORDS.has(w))) return "es-ES";
  return "en-US";
}

export function extractStyle(text: string): string {
  const lower = text.toLowerCase();
  for (const style of SUPPORTED_STYLES) {
    if (lower.includes(style)) return style;
  }
  return "default";
}
