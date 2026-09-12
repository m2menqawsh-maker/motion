import { useState, useEffect } from "react";

export interface BrandInfo {
  name: string;
  colors: {
    primary: string;
    backgroundLight: string;
    text: string;
  };
}

export interface WindowLayoutInfo {
  id: string;
  title: string;
  zIndex: number;
  startX: number;
  startY: number;
  startW: number;
  startH: number;
  enterAt: number;
}

export interface SceneConfig {
  enabled: boolean;
}

export interface VideoPropsData {
  cta: string;
  brand: BrandInfo;
  scenes: SceneConfig[];
  overlap: number;
  headlines: Record<string, string[]>;
  productFeatures: { title?: string; description?: string }[];
  windowLayout: WindowLayoutInfo[];
  cursorPath: any[]; 
  cursorStyle: { scale: number; rotation: number };
}

let globalState: VideoPropsData = {
  cta: "Get Started",
  brand: {
    name: "Brand",
    colors: { primary: "#6366F1", backgroundLight: "#FFFFFF", text: "#000000" },
  },
  scenes: [],
  overlap: 0,
  headlines: { closer: [] },
  productFeatures: [],
  windowLayout: [],
  cursorPath: [],
  cursorStyle: { scale: 1, rotation: 0 },
};

type Listener = (state: VideoPropsData) => void;
const listeners = new Set<Listener>();

export function updateProp(updater: (prev: VideoPropsData) => VideoPropsData): void {
  globalState = updater(globalState);
  listeners.forEach((l) => l(globalState));
}

function useGlobalState(): VideoPropsData {
  const [state, setState] = useState(globalState);
  useEffect(() => {
    listeners.add(setState);
    return () => {
      listeners.delete(setState);
    };
  }, []);
  return state;
}

export function useVideoProps(): VideoPropsData {
  return useGlobalState();
}

export function useBrand(): BrandInfo {
  return useGlobalState().brand;
}

export function useHeadlines(): Record<string, string[]> {
  return useGlobalState().headlines;
}

export function useWindowLayout(): WindowLayoutInfo[] {
  return useGlobalState().windowLayout;
}

export function useProductFeatures(): { title?: string; description?: string }[] {
  return useGlobalState().productFeatures;
}

export function useCursorPath(): any[] {
  return useGlobalState().cursorPath;
}

export function useCursorStyle(): { scale: number; rotation: number } {
  return useGlobalState().cursorStyle;
}
