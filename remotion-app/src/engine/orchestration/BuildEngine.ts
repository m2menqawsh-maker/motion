import { BuildResult, BuildPlanScene, VideoSpec, ValidationError } from './types';
import { resolveTemplate } from './TemplateResolver';
import { resolveProps } from './PropResolver';
import { resolveMedia } from './MediaResolver';
import { resolveTimeline } from './TimelineResolver';
import * as fs from 'fs';
import * as path from 'path';

export function buildVideo(spec: VideoSpec, options: { dryRun?: boolean } = {}): BuildResult {
  const errors: ValidationError[] = [];
  const warnings: ValidationError[] = [];
  const planScenes: BuildPlanScene[] = [];

  let mediaMissing = 0;

  // 1. Template & Contract Gate
  for (const scene of spec.scenes) {
    const { error, resolvedScene } = resolveTemplate(scene);
    if (error) {
      errors.push(error);
    }
    if (resolvedScene) {
      planScenes.push(resolvedScene);
    }
  }

  // 2. Props Gate
  for (const scene of planScenes) {
    const propsResult = resolveProps(scene);
    errors.push(...propsResult.errors);
    warnings.push(...propsResult.warnings);
  }

  // 3. Media Gate
  const mediaResult = resolveMedia(spec, planScenes);
  errors.push(...mediaResult.errors);
  warnings.push(...mediaResult.warnings);
  mediaMissing = mediaResult.missingCount;

  // 4. Timeline Gate
  const timelineResult = resolveTimeline(spec, planScenes);
  errors.push(...timelineResult.errors);
  warnings.push(...timelineResult.warnings);

  const success = errors.length === 0;

  const result: BuildResult = {
    success,
    durationInFrames: timelineResult.totalDurationInFrames > 0 ? timelineResult.totalDurationInFrames : spec.durationInFrames,
    plan: {
      resolution: { width: spec.width, height: spec.height },
      fps: spec.fps,
      duration: timelineResult.totalDurationInFrames,
      scenes: planScenes,
      assets: {
        total: (spec.assets ? Object.keys(spec.assets).length : 0),
        missing: mediaMissing,
      },
    },
    errors,
    warnings,
  };

  if (!options.dryRun && success) {
    // Generate the resolved spec file so SceneComposer can read it at runtime
    const specPath = path.join(__dirname, '../../../../ground-truth/orchestration_resolved_spec.json');
    fs.writeFileSync(specPath, JSON.stringify(result, null, 2), 'utf-8');
  }

  return result;
}
