import { CreativeCompiler } from '../../remotion-app/src/engine/planning/Compiler';
import { CreativeSpec } from '../../remotion-app/src/engine/planning/types';
import { RegistryClient } from '../../remotion-app/src/engine/catalog/RegistryClient';
import * as assert from 'assert';

const baseSpec: CreativeSpec = {
  schemaVersion: '1.0',
  id: 'test-compiler',
  format: { width: 1920, height: 1080, fps: 30 },
  scenes: [
    {
      role: 'text_hook',
      durationSeconds: 4,
      content: { headline: 'Test Headline' },
    }
  ],
};

function runTests() {
  let passed = 0;
  let failed = 0;

  const test = (name: string, fn: () => void) => {
    try {
      fn();
      console.log(`✅ ${name}`);
      passed++;
    } catch (e: any) {
      console.error(`❌ ${name}`);
      console.error(e.message);
      failed++;
    }
  };

  test('Test N — Registry Integration', () => {
    // text_hook must resolve through RegistryClient
    const result = CreativeCompiler.compile(baseSpec);
    assert.strictEqual(result.success, true);
    assert.ok(result.videoSpec);
    assert.strictEqual(result.videoSpec.scenes.length, 1);
    assert.strictEqual(result.videoSpec.scenes[0].templateId, 'elements/typography/text-reveal');
  });

  test('Test O — Certification Safety', () => {
    // We mock RegistryClient getCertificationStatus to simulate a BLOCKED template
    const orig = RegistryClient.getCertificationStatus;
    RegistryClient.getCertificationStatus = (id) => 'BLOCKED';
    
    const result = CreativeCompiler.compile(baseSpec);
    assert.strictEqual(result.success, false);
    assert.strictEqual(result.errors.length, 1);
    assert.match(result.errors[0].message, /NO_EXECUTABLE_TEMPLATE/);
    assert.match(result.errors[0].message, /not certified/);
    
    // Restore
    RegistryClient.getCertificationStatus = orig;
  });

  test('Test X — Missing Dependency Rejection (ChaosDesktop)', () => {
    const spec: CreativeSpec = {
      ...baseSpec,
      scenes: [
        {
          role: 'desktop_simulation',
          durationSeconds: 5,
        }
      ]
    };
    const result = CreativeCompiler.compile(spec);
    assert.strictEqual(result.success, false);
    assert.strictEqual(result.errors.length, 1);
    assert.strictEqual(result.errors[0].role, 'desktop_simulation');
    assert.match(result.errors[0].message, /NO_EXECUTABLE_TEMPLATE/);
    assert.match(result.errors[0].message, /required asset missing/);
    assert.match(result.errors[0].message, /typing\.mp3/);
  });

  test('Test P — Deterministic Compilation', () => {
    const result1 = CreativeCompiler.compile(baseSpec);
    const result2 = CreativeCompiler.compile(baseSpec);
    assert.deepStrictEqual(result1, result2);
  });

  test('Test Q — Provenance', () => {
    const spec: CreativeSpec = {
      ...baseSpec,
      scenes: [
        {
          role: 'text_hook',
          durationSeconds: 4,
          // Missing content.headline which the adapter requires
        }
      ]
    };
    const result = CreativeCompiler.compile(spec);
    assert.strictEqual(result.success, false);
    assert.strictEqual(result.errors.length, 1);
    assert.strictEqual(result.errors[0].sceneIndex, 0);
    assert.strictEqual(result.errors[0].role, 'text_hook');
    assert.match(result.errors[0].message, /Missing required semantic input "headline"/);
  });

  console.log(`\n--- Compiler Tests: ${passed} passed, ${failed} failed ---`);
  if (failed > 0) process.exit(1);
}

runTests();

