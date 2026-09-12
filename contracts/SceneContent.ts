export interface CaptionWord {
  word: string;
  startMs: number;
  endMs: number;
}

export interface SceneContent {
  lines?: string[];       // surface.text split by "\n"
  words?: CaptionWord[];  // captions_ref
  images?: string[];      // media_refs (type=image) resolved via manifest
  screen?: string;        // first media_ref (image|video)
  numbers?: number[];
  range?: { from: number; to: number };
  path?: string;
  icons?: string[];
  audioRef?: string;
  spectrum?: number[][];
}
