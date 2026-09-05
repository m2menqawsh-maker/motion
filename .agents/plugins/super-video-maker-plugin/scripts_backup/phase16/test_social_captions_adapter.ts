import { ADAPTER_REGISTRY } from '../../remotion-app/src/engine/planning/adapters/AdapterRegistry';
import assert from 'assert';

function runTest() {
  const adapter = ADAPTER_REGISTRY['social_captions_v1'];
  assert(adapter, 'social_captions_v1 adapter not found in registry');

  // Input creative spec caption format (as might be supplied by user or AI)
  const inputCaptions = [
    { word: "Hello", start: 0, end: 500 },
    { word: "World", start: 500, end: 1000 }
  ];

  const context: any = {
    templateId: 'scenes/social/SocialClip',
    content: {
      captions: inputCaptions,
      hookTitle: "Test Hook"
    },
    propIntelligence: {}
  };

  const output1 = adapter.adapt(context);
  const output2 = adapter.adapt(context);

  // Determinism test (Step 7)
  assert.strictEqual(JSON.stringify(output1), JSON.stringify(output2), "Outputs must be deterministic");

  // Output shape test
  assert(Array.isArray(output1.props.captions), 'Output props.captions should be an array');
  const captions = output1.props.captions as any[];
  assert.strictEqual(captions.length, 2, 'Should map 2 captions');

  assert.strictEqual(captions[0].text, 'Hello');
  assert.strictEqual(captions[0].startMs, 0);
  assert.strictEqual(captions[0].endMs, 500);

  // Unrelated props untouched
  assert.strictEqual(output1.props.hookTitle, "Test Hook", 'Unrelated props should remain untouched');

  // Empty captions test
  const emptyContext: any = {
    templateId: 'scenes/social/SocialClip',
    content: {
      hookTitle: "No captions here"
    },
    propIntelligence: {}
  };

  const emptyOutput = adapter.adapt(emptyContext);
  assert(Array.isArray(emptyOutput.props.captions), 'Output props.captions should be an empty array when no captions exist');
  assert.strictEqual(emptyOutput.props.captions.length, 0);

  console.log("social_captions_v1 adapter tests passed!");
}

runTest();
