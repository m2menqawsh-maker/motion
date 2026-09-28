import type { AssetRef } from "./asset-resolver";

export interface CaptionWord {
  word: string;
  startMs: number;
  endMs: number;
}

export interface SceneContent {
  lines?: string[];
  words?: CaptionWord[];
  images?: (string | AssetRef)[];
  screen?: string | AssetRef;
  numbers?: number[];
  range?: { from: number; to: number };
  path?: string;
  icons?: (string | AssetRef)[];
  audioRef?: string | AssetRef;
  spectrum?: number[][];
  text?: string;
}
