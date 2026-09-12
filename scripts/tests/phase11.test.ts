import * as assert from 'assert';
import { RegistryClient } from '../../remotion-app/src/engine/catalog/RegistryClient';

function createMockData() {
  const contracts = {
    templates: [
      { id: 'template/fully-supported', props: { headline: { required: true } } },
      { id: 'template/catalog-only', props: { description: { required: true } } },
      { id: 'template/broken-deps', props: { headline: { required: true } } }
    ]
  };

  const reports = {
    results: [
      { templateId: 'template/fully-supported', status: 'CERTIFIED' },
      { templateId: 'template/catalog-only', status: 'UNCERTIFIED' },
      { templateId: 'template/broken-deps', status: 'CERTIFIED' }
    ]
  };

  const registry = {
    schemaVersion: '1.0',
    registryVersion: '1.0.1',
    templates: [
      {
        templateId: 'template/fully-supported',
        semanticRoles: ['test_role'],
        capabilities: { content: ['headline'], visual: [], media: [], behavior: [] },
        selection: { enabled: true, priority: 100 },
        propIntelligence: { contentMapping: { headline: 'headline' }, mediaMapping: {}, requiredProps: ['headline'] },
        adapter: { capability: 'animated_text_v1', status: 'IMPLEMENTED' },
        assets: { dependencies: [], health: 'HEALTHY' },
        evidence: [],
        executionEligibility: 'FULLY_SUPPORTED'
      },
      {
        templateId: 'template/catalog-only',
        semanticRoles: ['test_role'],
        capabilities: { content: ['body_text'], visual: [], media: [], behavior: [] },
        selection: { enabled: true, priority: 50 },
        propIntelligence: { contentMapping: { description: 'body_text' }, mediaMapping: {}, requiredProps: ['description'] },
        adapter: { capability: 'UNKNOWN', status: 'CATALOG_ONLY' },
        assets: { dependencies: [], health: 'HEALTHY' },
        evidence: [],
        executionEligibility: 'CATALOG_ONLY'
      },
      {
        templateId: 'template/broken-deps',
        semanticRoles: ['test_role'],
        capabilities: { content: ['headline'], visual: [], media: [], behavior: [] },
        selection: { enabled: true, priority: 80 },
        propIntelligence: { contentMapping: { headline: 'headline' }, mediaMapping: {}, requiredProps: ['headline'] },
        adapter: { capability: 'animated_text_v1', status: 'IMPLEMENTED' },
        assets: {
          dependencies: [{ id: 'missing.mp3', kind: 'audio', required: true, status: 'MISSING' }],
          health: 'BROKEN'
        },
        evidence: [],
        executionEligibility: 'BROKEN' // Even though it's certified and has an adapter, it is broken
      }
    ]
  };

  return { contracts, reports, registry };
}

function runTests() {
  let passed = 0;
  let failed = 0;

  const test = (name: string, fn: () => void) => {
    try {
      RegistryClient.__clearTestingData();
      fn();
      console.log(`✅ ${name}`);
      passed++;
    } catch (e: any) {
      console.error(`❌ ${name}`);
      console.error(e.message);
      failed++;
    }
  };

  test('Test 1 — Execution Eligibility (FULLY_SUPPORTED vs CATALOG_ONLY vs BROKEN)', () => {
    const { contracts, reports, registry } = createMockData();
    RegistryClient.__setTestingData(registry, contracts, reports);
    
    // Normal query finds all templates if we don't require an adapter
    const all = RegistryClient.findTemplates({ role: 'test_role' });
    assert.strictEqual(all.length, 3, 'Should find fully-supported, catalog-only, and broken');
    
    // Query requiring adapter strictly excludes CATALOG_ONLY and BROKEN
    const executable = RegistryClient.findTemplates({ role: 'test_role', requireAdapter: true });
    assert.strictEqual(executable.length, 1, 'Should only find fully-supported');
    assert.strictEqual(executable[0].templateId, 'template/fully-supported');
    assert.strictEqual(executable[0].executionEligibility, 'FULLY_SUPPORTED');
  });

  test('Test 2 — Dynamic Eligibility Calculation (Uncertified override)', () => {
    const { contracts, reports, registry } = createMockData();
    // Simulate user locally revoking certification
    reports.results.find(r => r.templateId === 'template/fully-supported')!.status = 'UNCERTIFIED';
    RegistryClient.__setTestingData(registry, contracts, reports);
    
    const candidates = RegistryClient.findTemplates({ role: 'test_role', requireAdapter: true });
    // It should now be dynamically calculated as CATALOG_ONLY, so requireAdapter filters it out
    assert.strictEqual(candidates.length, 0);
  });

  test('Test 3 — Preferred Capabilities Sorting', () => {
    const { contracts, reports, registry } = createMockData();
    // We add another fully supported template with body_text capability
    registry.templates.push({
      templateId: 'template/fully-supported-2',
      semanticRoles: ['test_role'],
      capabilities: { content: ['body_text'], visual: [], media: [], behavior: [] },
      selection: { enabled: true, priority: 100 },
      propIntelligence: { contentMapping: { description: 'body_text' }, mediaMapping: {}, requiredProps: ['description'] },
      adapter: { capability: 'test_v1', status: 'IMPLEMENTED' },
      assets: { dependencies: [], health: 'HEALTHY' },
      evidence: [],
      executionEligibility: 'FULLY_SUPPORTED'
    } as any);
    
    // Make both CERTIFIED
    reports.results.push({ templateId: 'template/fully-supported-2', status: 'CERTIFIED' });
    
    RegistryClient.__setTestingData(registry, contracts, reports);
    
    const candidates = RegistryClient.findTemplates({ 
      role: 'test_role', 
      requireAdapter: true,
      preferredCapabilities: { content: ['body_text'] }
    });
    
    assert.strictEqual(candidates.length, 2);
    // Because we preferred body_text, fully-supported-2 should be first despite same priority
    assert.strictEqual(candidates[0].templateId, 'template/fully-supported-2');
    assert.strictEqual(candidates[1].templateId, 'template/fully-supported');
  });

  console.log(`\n--- Phase 11 Tests: ${passed} passed, ${failed} failed ---`);
  if (failed > 0) process.exit(1);
}

runTests();
