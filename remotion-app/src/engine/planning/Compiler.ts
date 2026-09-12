import { CreativeSpec, CompilationResult, CompilationError } from './types';
import { adaptProps } from './TemplateAdapter';
import { RegistryClient } from '../catalog/RegistryClient';
import { VideoSpec, SceneSpec } from '../orchestration/types';

export class CreativeCompiler {
  public static compile(creativeSpec: CreativeSpec): CompilationResult {
    const errors: CompilationError[] = [];

    if (creativeSpec.schemaVersion !== '1.0') {
      errors.push({
        message: `Unsupported schema version: ${creativeSpec.schemaVersion}`,
      });
      return { success: false, errors };
    }

    const { width, height, fps } = creativeSpec.format;
    const compiledScenes: SceneSpec[] = [];
    let currentStartFrame = 0;

    for (let i = 0; i < creativeSpec.scenes.length; i++) {
      const scene = creativeSpec.scenes[i];
      
      let candidates = RegistryClient.findTemplates({ role: scene.role }); // Don't filter executable yet
      if ((scene as any).templateIdHint) {
        candidates = candidates.filter(c => c.templateId === (scene as any).templateIdHint);
      }
      
      if (candidates.length === 0) {
        errors.push({
          sceneIndex: i,
          role: scene.role,
          message: `No template exists in the catalog for semantic role "${scene.role}".`,
        });
        continue;
      }

      // Check if there is an executable candidate
      const executableCandidates = candidates.filter(c => c.executionEligibility === 'FULLY_SUPPORTED');
      
      if (executableCandidates.length === 0) {
        const candidateReasons = candidates.map(c => {
          let reason = '';
          if (c.executionEligibility === 'BROKEN') {
            const missingDep = c.assets.dependencies.find(d => d.required && d.status === 'MISSING');
            reason = `required asset missing (${missingDep?.id})`;
          } else if (c.adapter.status !== 'IMPLEMENTED') {
            reason = 'adapter not implemented';
          } else {
            reason = 'not certified';
          }
          return `  - ${c.templateId} → ${c.executionEligibility}: ${reason}`;
        }).join('\n');

        errors.push({
          sceneIndex: i,
          role: scene.role,
          message: `NO_EXECUTABLE_TEMPLATE\n\nRole: ${scene.role}\n\nCandidates:\n${candidateReasons}\n\nNo executable template satisfies the requested scene.`,
        });
        continue;
      }

      const selectedCandidate = executableCandidates[0];

      const { result, error } = adaptProps(scene.role, selectedCandidate, scene.content);
      
      if (error) {
        error.sceneIndex = i;
        errors.push(error);
        continue;
      }
      if (!result) continue; // Should not happen if there is no error

      // Deterministic Duration Conversion
      // Default to 5 seconds if durationIntent is omitted, for minimal proof mapping.
      const durationSeconds = scene.durationSeconds || 5;
      const durationInFrames = Math.round(durationSeconds * fps);

      compiledScenes.push({
        id: `scene-${i}`,
        templateId: selectedCandidate.templateId,
        props: result,
        startFrame: currentStartFrame,
        durationInFrames,
      });

      // Sequential Timeline: The next scene starts right after this one ends
      currentStartFrame += durationInFrames;
    }

    if (errors.length > 0) {
      return { success: false, errors };
    }

    const videoSpec: VideoSpec = {
      id: creativeSpec.id,
      width,
      height,
      fps,
      durationInFrames: currentStartFrame,
      scenes: compiledScenes,
      assets: {}, // No asset resolution in this phase
    };

    return {
      success: true,
      videoSpec,
      errors: [],
    };
  }
}
