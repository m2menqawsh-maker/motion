import { BuildPlanScene, ValidationError, VideoSpec } from './types';

export function resolveTimeline(spec: VideoSpec, scenes: BuildPlanScene[]): {
  errors: ValidationError[];
  warnings: ValidationError[];
  totalDurationInFrames: number;
} {
  const errors: ValidationError[] = [];
  const warnings: ValidationError[] = [];
  let calculatedDuration = 0;

  if (spec.durationInFrames <= 0 || !isFinite(spec.durationInFrames) || isNaN(spec.durationInFrames)) {
    errors.push({
      code: 'INVALID_TIMELINE',
      stage: 'TIMELINE_GATE',
      prop: 'durationInFrames',
      message: `Global durationInFrames is invalid: ${spec.durationInFrames}`,
      severity: 'ERROR',
    });
  }

  // Sort scenes by startFrame
  const sorted = [...scenes].sort((a, b) => a.spec.startFrame - b.spec.startFrame);

  let lastEnd = 0;

  for (const scene of sorted) {
    const s = scene.spec;

    if (s.durationInFrames <= 0 || !isFinite(s.durationInFrames) || isNaN(s.durationInFrames)) {
      errors.push({
        code: 'INVALID_TIMELINE',
        stage: 'TIMELINE_GATE',
        templateId: s.templateId,
        prop: 'durationInFrames',
        message: `Scene durationInFrames is invalid: ${s.durationInFrames}`,
        severity: 'ERROR',
      });
      continue;
    }

    if (s.startFrame < 0 || !isFinite(s.startFrame) || isNaN(s.startFrame)) {
      errors.push({
        code: 'INVALID_TIMELINE',
        stage: 'TIMELINE_GATE',
        templateId: s.templateId,
        prop: 'startFrame',
        message: `Scene startFrame is invalid: ${s.startFrame}`,
        severity: 'ERROR',
      });
      continue;
    }

    const sceneEnd = s.startFrame + s.durationInFrames;
    if (sceneEnd > calculatedDuration) {
      calculatedDuration = sceneEnd;
    }

    if (s.startFrame < lastEnd) {
      warnings.push({
        code: 'TIMELINE_OVERLAP',
        stage: 'TIMELINE_GATE',
        templateId: s.templateId,
        message: `Scene starts at ${s.startFrame} before previous scene ends at ${lastEnd}`,
        severity: 'WARNING',
      });
    }

    if (s.startFrame > lastEnd) {
      warnings.push({
        code: 'TIMELINE_GAP',
        stage: 'TIMELINE_GATE',
        templateId: s.templateId,
        message: `Timeline gap between ${lastEnd} and ${s.startFrame}`,
        severity: 'WARNING',
      });
    }

    lastEnd = sceneEnd;
  }

  if (calculatedDuration !== spec.durationInFrames && errors.length === 0) {
    warnings.push({
      code: 'DURATION_MISMATCH',
      stage: 'TIMELINE_GATE',
      message: `Global duration (${spec.durationInFrames}) does not match calculated scene duration (${calculatedDuration})`,
      severity: 'WARNING',
    });
  }

  return { errors, warnings, totalDurationInFrames: calculatedDuration };
}
