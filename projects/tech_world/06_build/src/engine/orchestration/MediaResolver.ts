import { BuildPlanScene, ValidationError, VideoSpec } from './types';

export function resolveMedia(spec: VideoSpec, scenes: BuildPlanScene[]): {
  errors: ValidationError[];
  warnings: ValidationError[];
  missingCount: number;
} {
  const errors: ValidationError[] = [];
  const warnings: ValidationError[] = [];
  let missingCount = 0;

  // Validate global assets if any
  if (spec.assets) {
    for (const [key, value] of Object.entries(spec.assets)) {
      if (isUnsafePath(value)) {
        errors.push({
          code: 'INVALID_MEDIA_PATH',
          stage: 'MEDIA_GATE',
          prop: `assets.${key}`,
          message: `Asset path contains illegal absolute path: ${value}`,
          severity: 'ERROR',
        });
        missingCount++;
      }
    }
  }

  // Validate scene props bounded to 1 level (no deep recursion to save performance)
  for (const scene of scenes) {
    for (const [propName, value] of Object.entries(scene.normalizedProps)) {
      if (typeof value === 'string' && isUnsafePath(value)) {
        errors.push({
          code: 'INVALID_MEDIA_PATH',
          stage: 'MEDIA_GATE',
          templateId: scene.spec.templateId,
          prop: propName,
          message: `Prop contains illegal absolute path: ${value}`,
          severity: 'ERROR',
        });
        missingCount++;
      } else if (typeof value === 'string' && isMissingPlaceholder(value)) {
        errors.push({
          code: 'MEDIA_NOT_FOUND',
          stage: 'MEDIA_GATE',
          templateId: scene.spec.templateId,
          prop: propName,
          message: `Prop contains missing/placeholder media: ${value}`,
          severity: 'ERROR',
        });
        missingCount++;
      }
    }
  }

  return { errors, warnings, missingCount };
}

function isUnsafePath(p: string): boolean {
  const lower = p.toLowerCase();
  return lower.includes('c:/') || lower.includes('c:\\') || lower.includes('d:/') || lower.includes('d:\\');
}

function isMissingPlaceholder(p: string): boolean {
  return p.includes('MISSING_ASSET') || p.includes('NOT_FOUND');
}
