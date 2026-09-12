import fs from 'fs';
import path from 'path';

const ROOT_DIR = process.cwd();
const BATCH_OUT = path.join(ROOT_DIR, 'ground-truth/phase_16_3_runtime_batch.json');

function main() {
  const creativeSpec = {
    schemaVersion: "1.0",
    creativeId: "phase16-3-social-captions",
    id: "phase16_3_batch",
    version: "1.0",
    format: {
      width: 1080,
      height: 1920,
      fps: 30
    },
    intent: "social_promo",
    mood: "dynamic",
    scenes: [
      {
        role: "generic_component",
        durationSeconds: 4,
        content: {
          hookTitle: "Social Clip Default",
          captions: [
            { text: "This", startMs: 0, endMs: 1000 },
            { text: "is", startMs: 1000, endMs: 2000 },
            { text: "SocialClip", startMs: 2000, endMs: 4000 }
          ]
        },
        templateIdHint: "scenes/social/SocialClip"
      },
      {
        role: "generic_component",
        durationSeconds: 4,
        content: {
          hookTitle: "Social Clip Index",
          captions: [
            { word: "And", start: 0, end: 1000 },
            { word: "social-clip/index", start: 1000, end: 4000 }
          ]
        },
        templateIdHint: "scenes/social/social-clip/index"
      },
      {
        role: "text_hook",
        durationSeconds: 4,
        content: {
          headline: "Control Template",
          body_text: "Testing generic execution hasn't regressed"
        },
        templateIdHint: "effects/transitions/blur-out-up"
      }
    ]
  };

  fs.writeFileSync(BATCH_OUT, JSON.stringify(creativeSpec, null, 2));
  console.log(`Generated runtime batch at ${BATCH_OUT}`);
}

main();
