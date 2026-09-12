import { PropIntelligence } from '../catalog/types';
import { CompilationError } from './types';
import { AdapterDefinition } from './adapters/types';

export class SemanticContentResolver {
  public static resolve(
    role: string,
    creativeContent: Record<string, unknown> | undefined,
    adapter: AdapterDefinition,
    propIntelligence: PropIntelligence
  ): { resolvedContent?: Record<string, unknown>; error?: CompilationError } {
    const content = creativeContent || {};
    const resolved: Record<string, unknown> = {};

    // 1. Verify required semantic inputs by the adapter
    for (const req of adapter.requiredSemanticInputs) {
      if (content[req] === undefined) {
        return {
          error: {
            role,
            message: `Missing required semantic input "${req}" for adapter capability "${adapter.capability}".`,
          }
        };
      }
    }

    // 2. Map semantic content to physical props based on PropIntelligence
    for (const [semanticKey, value] of Object.entries(content)) {
      // Find the physical key(s) mapped to this semantic key
      // contentMapping: { physicalKey: semanticKey }
      const mappedPhysicalKeys = Object.entries(propIntelligence.contentMapping)
        .filter(([_, sem]) => sem === semanticKey)
        .map(([phys]) => phys);
      
      const mappedMediaKeys = Object.entries(propIntelligence.mediaMapping)
        .filter(([_, sem]) => sem === semanticKey)
        .map(([phys]) => phys);

      const allPhysicalKeys = [...mappedPhysicalKeys, ...mappedMediaKeys];

      // If mapped, assign the value to the physical keys
      for (const physKey of allPhysicalKeys) {
        resolved[physKey] = value;
      }
      
      // Also preserve the original semantic key in case the adapter uses it directly
      resolved[semanticKey] = value;
    }

    // 3. Verify required physical props according to the template
    for (const req of propIntelligence.requiredProps) {
      if (resolved[req] === undefined) {
        return {
          error: {
            role,
            message: `Semantic mapping failed: Template requires physical prop "${req}", but no provided semantic input mapped to it.`,
          }
        };
      }
    }

    return { resolvedContent: resolved };
  }
}
