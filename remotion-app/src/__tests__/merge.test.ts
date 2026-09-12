import { describe, it, expect, vi } from 'vitest';
import { mergeScene } from '../merge';
import { BlueprintScene } from '../../../contracts/blueprint';

describe('mergeScene and Zod schema consistency', () => {
  it('should validate scene props against Zod and return surface', () => {
    const brand = { brandName: 'Test', logoSrc: null, colors: {} as any, fonts: {} as any };
    const scene: BlueprintScene = {
      scene_id: 's1',
      template: 'TestTemplate',
      startFrame: 0,
      durationFrames: 100
    };
    
    // Simulate template defaults
    const registryEntry = {
      id: 'TestTemplate',
      name: 'TestTemplate',
      defaults: {
        fontSize: 30,
        opacity: 1
      },
      schema: {} as any,
      component: () => null
    };

    const merged = mergeScene(scene, registryEntry, brand);
    expect(merged.surface.fontSize).toBe(30);
    expect(merged.surface.opacity).toBe(1);
  });

  it('should throw Zod error for invalid style override in surface', () => {
    const brand = { brandName: 'Test', logoSrc: null, colors: {} as any, fonts: {} as any };
    const scene: BlueprintScene = {
      scene_id: 's1',
      template: 'TestTemplate',
      startFrame: 0,
      durationFrames: 100,
      props: {
        opacity: 2 // Invalid, should be 0-1
      }
    };
    
    const registryEntry = {
      id: 'TestTemplate',
      name: 'TestTemplate',
      defaults: {
        opacity: 1
      },
      schema: {} as any,
      component: () => null
    };

    expect(() => mergeScene(scene, registryEntry, brand)).toThrow(/Too big/);
  });
});
