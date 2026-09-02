import * as fs from 'fs';
import * as path from 'path';

const ROOT_DIR = path.resolve(__dirname, '../../');
const COHORTS_PATH = path.join(ROOT_DIR, 'ground-truth/phase_15_execution_cohorts.json');
const BATCH_OUT = path.join(ROOT_DIR, 'scratch/test_batch_3.json');
const SAMPLES_OUT = path.join(ROOT_DIR, 'ground-truth/phase_15_runtime_samples.json');

function main() {
  const cohorts = JSON.parse(fs.readFileSync(COHORTS_PATH, 'utf-8'));
  
  const scenes = [];
  const sampledTemplates: string[] = [];

  for (const c of cohorts) {
    for (const t of c.representativeTemplates) {
      sampledTemplates.push(t);
      
      // Assign role based on cohort id or default to static_scene if it's static
      let role = 'static_scene';
      if (c.cohortId === 'generic_text') role = 'text_hook';
      if (c.cohortId === 'generic_effect') role = 'visual_effect';
      if (c.cohortId === 'generic_transition') role = 'transition';
      if (c.cohortId === 'generic_ui') role = 'ui_simulation';
      
      scenes.push({
        role,
        durationSeconds: 2,
        content: {
          headline: "Sample Run " + c.cohortId,
          body_text: "Testing generic execution"
        },
        templateIdHint: t
      });
    }
  }

  const creativeSpec = {
    schemaVersion: "1.0",
    creativeId: "phase15-samples",
    id: "phase15_samples",
    version: "1.0",
    format: {
      width: 1080,
      height: 1920,
      fps: 30
    },
    intent: "product_demo",
    mood: "dynamic",
    scenes
  };

  fs.writeFileSync(BATCH_OUT, JSON.stringify(creativeSpec, null, 2));
  fs.writeFileSync(SAMPLES_OUT, JSON.stringify({ sampledTemplates }, null, 2));
  
  console.log(`Generated creative spec with ${scenes.length} scenes.`);
}

main();
