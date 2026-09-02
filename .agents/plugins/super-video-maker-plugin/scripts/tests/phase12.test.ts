import * as assert from 'assert';
import { RegistryClient } from '../../remotion-app/src/engine/catalog/RegistryClient';
import { CreativeCompiler } from '../../remotion-app/src/engine/planning/Compiler';
import { CreativeSpec } from '../../remotion-app/src/engine/planning/types';
import { SemanticContentResolver } from '../../remotion-app/src/engine/planning/SemanticContentResolver';
import { ADAPTER_REGISTRY } from '../../remotion-app/src/engine/planning/adapters/AdapterRegistry';

const baseSpec: CreativeSpec = {
  schemaVersion: '1.0',
  format: { width: 1080, height: 1920, fps: 30 },
  config: { format: 'vertical', theme: 'default', globalAudio: 'none' },
  scenes: []
};

function runTests() {
  console.log('--- STARTING PHASE 12 TESTS ---');
  let passed = 0;
  let failed = 0;

  function test(name: string, fn: () => void) {
    try {
      fn();
      console.log(`✅ ${name}`);
      passed++;
    } catch (e: any) {
      console.error(`❌ ${name}`);
      console.error(e.message);
      failed++;
    }
  }

  // Load standard registry
  RegistryClient.loadCatalogs();

  test('Test A — Adapter Registry (Known Implemented Capability)', () => {
    const def = ADAPTER_REGISTRY['animated_text_v1'];
    assert.ok(def, 'animated_text_v1 should exist in registry');
    assert.ok(def.requiredSemanticInputs.includes('headline'));
  });

  test('Test B — Unknown Adapter', () => {
    const def = ADAPTER_REGISTRY['unknown_adapter_v999'];
    assert.strictEqual(def, undefined, 'Unknown adapter should not resolve');
  });

  test('Test C — Semantic Prop Resolution', () => {
    const def = ADAPTER_REGISTRY['animated_text_v1'];
    const propIntel = {
      contentMapping: { physical_text: 'headline' },
      mediaMapping: {},
      requiredProps: ['physical_text'],
      confidence: 'PROVEN' as const
    };
    const { resolvedContent, error } = SemanticContentResolver.resolve(
      'text_hook',
      { headline: 'Hello World' },
      def,
      propIntel
    );
    assert.strictEqual(error, undefined);
    assert.strictEqual(resolvedContent?.['physical_text'], 'Hello World');
    assert.strictEqual(resolvedContent?.['headline'], 'Hello World'); // Preserved
  });

  test('Test D — Missing Semantic Input', () => {
    const def = ADAPTER_REGISTRY['animated_text_v1'];
    const propIntel = {
      contentMapping: { physical_text: 'headline' },
      mediaMapping: {},
      requiredProps: ['physical_text'],
      confidence: 'PROVEN' as const
    };
    const { resolvedContent, error } = SemanticContentResolver.resolve(
      'text_hook',
      { body: 'Missing headline' },
      def,
      propIntel
    );
    assert.ok(error, 'Should produce error');
    assert.match(error!.message, /Missing required semantic input "headline"/);
  });

  test('Test E — Catalog Only', () => {
    // We mock the registry so animated-text is CATALOG_ONLY by setting it uncertified
    const orig = RegistryClient.getCertificationStatus;
    RegistryClient.getCertificationStatus = () => 'BLOCKED';
    
    const spec: CreativeSpec = {
      ...baseSpec,
      scenes: [{ role: 'text_hook', durationSeconds: 4, content: { headline: 'Test' } }]
    };
    const result = CreativeCompiler.compile(spec);
    assert.strictEqual(result.success, false);
    assert.match(result.errors[0].message, /NO_EXECUTABLE_TEMPLATE/);
    assert.match(result.errors[0].message, /not certified/);
    
    RegistryClient.getCertificationStatus = orig;
  });

  test('Test F — Broken Template', () => {
    const spec: CreativeSpec = {
      ...baseSpec,
      scenes: [{ role: 'desktop_simulation', durationSeconds: 4 }]
    };
    const result = CreativeCompiler.compile(spec);
    assert.strictEqual(result.success, false);
    assert.match(result.errors[0].message, /NO_EXECUTABLE_TEMPLATE/);
    assert.match(result.errors[0].message, /required asset missing/);
  });

  test('Test G — Fully Supported', () => {
    const spec: CreativeSpec = {
      ...baseSpec,
      scenes: [{ role: 'text_hook', durationSeconds: 4, content: { headline: 'Valid Hook' } }]
    };
    const result = CreativeCompiler.compile(spec);
    assert.strictEqual(result.success, true);
    assert.ok(result.videoSpec);
    assert.strictEqual(result.videoSpec.scenes[0].props.text, 'Valid Hook');
  });

  test('Test H — Determinism', () => {
    const spec: CreativeSpec = {
      ...baseSpec,
      scenes: [{ role: 'text_hook', durationSeconds: 4, content: { headline: 'Valid Hook' } }]
    };
    const result1 = CreativeCompiler.compile(spec);
    const result2 = CreativeCompiler.compile(spec);
    assert.deepStrictEqual(result1, result2);
  });

  test('Test I — Adapter Family Isolation', () => {
    const spec: CreativeSpec = {
      ...baseSpec,
      scenes: [{ role: 'text_hook', durationSeconds: 4, content: { not_headline: 'Invalid' } }]
    };
    const result = CreativeCompiler.compile(spec);
    assert.strictEqual(result.success, false);
    // Even though it's animated-text, the SemanticContentResolver will reject it because headline is missing
    assert.match(result.errors[0].message, /Missing required semantic input "headline"/);
  });

  test('Test J — No Fake Fallback', () => {
    const spec: CreativeSpec = {
      ...baseSpec,
      scenes: [{ role: 'unknown_role', durationSeconds: 4 }]
    };
    const result = CreativeCompiler.compile(spec);
    assert.strictEqual(result.success, false);
    assert.match(result.errors[0].message, /No template exists/);
  });

  test('Test K — Registry Query', () => {
    const candidates = RegistryClient.findTemplates({ role: 'text_hook', requireExecutable: true });
    for (const c of candidates) {
      assert.strictEqual(c.executionEligibility, 'FULLY_SUPPORTED');
    }
  });

  console.log(`\n--- Test Results: ${passed} passed, ${failed} failed ---`);
  if (failed > 0) process.exit(1);
}

runTests();
