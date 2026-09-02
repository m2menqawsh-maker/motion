export type ValidationSeverity = 'ERROR' | 'WARNING';

export interface ValidationError {
  code: string;
  stage: string;
  templateId?: string;
  prop?: string;
  message: string;
  severity: ValidationSeverity;
}

export interface TransitionSpec {
  type: string;
  durationInFrames: number;
}

export interface SceneSpec {
  id: string;
  templateId: string;
  props?: Record<string, any>;
  durationInFrames: number;
  startFrame: number;
  transition?: TransitionSpec;
}

export interface VideoSpec {
  id: string;
  width: number;
  height: number;
  fps: number;
  durationInFrames: number;
  scenes: SceneSpec[];
  assets?: Record<string, string>;
  metadata?: Record<string, any>;
}

export interface BuildPlanScene {
  spec: SceneSpec;
  normalizedProps: Record<string, any>;
  componentExportName: string;
  componentImportPath: string;
  status: string;
}

export interface BuildResult {
  success: boolean;
  durationInFrames: number;
  plan: {
    resolution: { width: number; height: number };
    fps: number;
    duration: number;
    scenes: BuildPlanScene[];
    assets: {
      total: number;
      missing: number;
    };
  };
  errors: ValidationError[];
  warnings: ValidationError[];
}
