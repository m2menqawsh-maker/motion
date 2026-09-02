export interface CreativeScene {
  role: string;
  durationSeconds?: number;
  content?: Record<string, any>;
  media?: Record<string, any>;
}

export interface CreativeFormat {
  width: number;
  height: number;
  fps: number;
}

export interface CreativeSpec {
  schemaVersion: string;
  id: string;
  format: CreativeFormat;
  scenes: CreativeScene[];
}

export interface CompilationError {
  sceneIndex?: number;
  role?: string;
  message: string;
}

export interface CompilationResult {
  success: boolean;
  videoSpec?: any; // To be mapped to orchestration/VideoSpec
  errors: CompilationError[];
}
