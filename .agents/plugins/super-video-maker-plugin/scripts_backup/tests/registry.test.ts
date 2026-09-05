import * as assert from 'assert';
import { RegistryClient, RegistryValidationError } from '../../remotion-app/src/engine/catalog/RegistryClient';

function createMockData() {
  const contracts = {
    templates: [
      { id: 'template/a' },
      { id: 'template/b' },
      { id: 'scenes/hooks/animated-text' },
      { id: 'scenes/ChaosDesktop' }
    ]
  };

  const reports = {
    results: [
      { templateId: 'template/a', status: 'CERTIFIED' },
      { templateId: 'template/b', status: 'CERTIFIED' },
      { templateId: 'scenes/hooks/animated-text', status: 'CERTIFIED' },
      { templateId: 'scenes/ChaosDesktop', status: 'CERTIFIED' }
    ]
  };

  const registry = {
    schemaVersion: '1.0',
    registryVersion: '1.0.0',
    templates: [
      {
        templateId: 'scenes/hooks/animated-text',
        semanticRoles: ['text_hook'],
        selection: { enabled: true, priority: 100 },
        adapter: { capability: 'animated_text_v1' },
        assets: { dependencies: [] }
      },
      {
        templateId: 'scenes/ChaosDesktop',
        semanticRoles: ['desktop_simulation'],
        selection: { enabled: true, priority: 50 },
        adapter: { capability: 'chaos_desktop_v1' },
        assets: {
          dependencies: [
            {
              id: 'typing.mp3',
              kind: 'audio',
              source: 'MANUAL_OBSERVATION',
              required: true,
              status: 'UNDECLARED'
            }
          ]
        }
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

  test('Test A — Registry Loads', () => {
    const { contracts, reports, registry } = createMockData();
    RegistryClient.__setTestingData(registry, contracts, reports);
    RegistryClient.loadCatalogs(); // Should not throw
    assert.ok(true);
  });

  test('Test B — Role Lookup', () => {
    const { contracts, reports, registry } = createMockData();
    RegistryClient.__setTestingData(registry, contracts, reports);
    const candidates = RegistryClient.findTemplates({ role: 'text_hook' });
    assert.strictEqual(candidates.length, 1);
    assert.strictEqual(candidates[0].templateId, 'scenes/hooks/animated-text');
  });

  test('Test C — Certification Filtering', () => {
    const { contracts, reports, registry } = createMockData();
    reports.results.find(r => r.templateId === 'scenes/hooks/animated-text')!.status = 'BLOCKED';
    RegistryClient.__setTestingData(registry, contracts, reports);
    const candidates = RegistryClient.findTemplates({ role: 'text_hook' });
    assert.strictEqual(candidates.length, 0); // Should be filtered out
  });

  test('Test D — Priority Ordering', () => {
    const { contracts, reports, registry } = createMockData();
    registry.templates.push({
      templateId: 'template/a',
      semanticRoles: ['text_hook'],
      capabilities: { content: [], visual: [], media: [], behavior: [] },
      selection: { enabled: true, priority: 200 }, // Higher priority
      adapter: { capability: 'test' },
      assets: { dependencies: [], health: 'HEALTHY' },
      evidence: []
    } as any);
    RegistryClient.__setTestingData(registry, contracts, reports);
    const candidates = RegistryClient.findTemplates({ role: 'text_hook' });
    assert.strictEqual(candidates.length, 2);
    assert.strictEqual(candidates[0].templateId, 'template/a');
  });

  test('Test E — Stable Tie Breaking', () => {
    const { contracts, reports, registry } = createMockData();
    registry.templates = [
      {
        templateId: 'template/b',
        semanticRoles: ['test_role'],
        selection: { enabled: true, priority: 100 },
        adapter: { capability: 'test' },
        assets: { dependencies: [], health: 'HEALTHY' }
      },
      {
        templateId: 'template/a',
        semanticRoles: ['test_role'],
        selection: { enabled: true, priority: 100 },
        adapter: { capability: 'test' },
        assets: { dependencies: [], health: 'HEALTHY' }
      }
    ] as any;
    RegistryClient.__setTestingData(registry, contracts, reports);
    const candidates = RegistryClient.findTemplates({ role: 'test_role' });
    assert.strictEqual(candidates.length, 2);
    // 'template/a' comes before 'template/b' lexically
    assert.strictEqual(candidates[0].templateId, 'template/a');
    assert.strictEqual(candidates[1].templateId, 'template/b');
  });

  test('Test F — Missing Role', () => {
    const { contracts, reports, registry } = createMockData();
    RegistryClient.__setTestingData(registry, contracts, reports);
    const candidates = RegistryClient.findTemplates({ role: 'unknown_role' });
    assert.strictEqual(candidates.length, 0);
  });

  test('Test G & H — Asset Metadata & Provenance', () => {
    const { contracts, reports, registry } = createMockData();
    RegistryClient.__setTestingData(registry, contracts, reports);
    const candidates = RegistryClient.findTemplates({ role: 'desktop_simulation' });
    // Note: Health filtering shouldn't exclude BROKEN candidates according to our new rules (compiler handles it).
    // Wait, findTemplates does exclude BROKEN templates right now in the original code, but we just removed it from RegistryClient!
    assert.strictEqual(candidates[0].assets.dependencies[0].id, 'typing.mp3');
    assert.strictEqual(candidates[0].assets.dependencies[0].source, 'MANUAL_OBSERVATION');
    assert.strictEqual(candidates[0].assets.dependencies[0].status, 'UNDECLARED');
  });

  test('Test I — Duplicate Template ID', () => {
    const { contracts, reports, registry } = createMockData();
    registry.templates.push(registry.templates[0]); // Duplicate
    RegistryClient.__setTestingData(registry, contracts, reports);
    assert.throws(() => RegistryClient.loadCatalogs(), RegistryValidationError);
  });

  test('Test J — Invalid Registry Schema', () => {
    const { contracts, reports, registry } = createMockData();
    registry.schemaVersion = '2.0';
    RegistryClient.__setTestingData(registry, contracts, reports);
    assert.throws(() => RegistryClient.loadCatalogs(), RegistryValidationError);
  });

  test('Test K — Unknown Template', () => {
    const { contracts, reports, registry } = createMockData();
    registry.templates.push({
      templateId: 'fake-template',
      semanticRoles: ['test_role'],
      selection: { enabled: true, priority: 100 },
      adapter: { capability: 'test' },
      assets: { dependencies: [] }
    } as any);
    RegistryClient.__setTestingData(registry, contracts, reports);
    assert.throws(() => RegistryClient.loadCatalogs(), RegistryValidationError);
  });

  test('Test L — Disabled Template', () => {
    const { contracts, reports, registry } = createMockData();
    registry.templates[0].selection.enabled = false;
    RegistryClient.__setTestingData(registry, contracts, reports);
    const candidates = RegistryClient.findTemplates({ role: 'text_hook' });
    assert.strictEqual(candidates.length, 0);
  });

  test('Test M — Capability Filtering', () => {
    const { contracts, reports, registry } = createMockData();
    registry.templates[0].capabilities = {
      content: ['headline'],
      visual: ['hero'],
      media: [],
      behavior: ['animated']
    } as any;
    RegistryClient.__setTestingData(registry, contracts, reports);
    
    // Should match
    const cand1 = RegistryClient.findTemplates({ 
      role: 'text_hook', 
      requiredCapabilities: { content: ['headline'] } 
    });
    assert.strictEqual(cand1.length, 1);

    // Should not match
    const cand2 = RegistryClient.findTemplates({ 
      role: 'text_hook', 
      requiredCapabilities: { content: ['body_text'] } 
    });
    assert.strictEqual(cand2.length, 0);
  });

  console.log(`\n--- Registry Tests: ${passed} passed, ${failed} failed ---`);
  if (failed > 0) process.exit(1);
}

runTests();
