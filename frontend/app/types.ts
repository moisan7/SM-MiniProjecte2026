export interface Coordinate {
  x: number;
  y: number;
}

export interface ProcessResponse {
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
  warning?: string;
}

export interface HistoryPage {
  items: ProcessResponse[];
  next_page_token: string | null;
}
