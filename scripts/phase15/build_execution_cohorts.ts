import * as fs from 'fs';
import * as path from 'path';

const ROOT_DIR = path.resolve(__dirname, '../../');
const VALIDATION_PATH = path.join(ROOT_DIR, 'ground-truth/phase_15_contract_validation.json');
const REGISTRY_PATH = path.join(ROOT_DIR, 'remotion-app/src/engine/catalog/registry.json');
const COHORTS_OUT = path.join(ROOT_DIR, 'ground-truth/phase_15_execution_cohorts.json');

function main() {
  const validation = JSON.parse(fs.readFileSync(VALIDATION_PATH, 'utf-8'));
  const registry = JSON.parse(fs.readFileSync(REGISTRY_PATH, 'utf-8')).templates;

  const cohorts: Record<string, any> = {};

  for (const templateId of validation.validTemplatesList) {
    const regEntry = registry.find((r: any) => r.templateId === templateId);
    if (!regEntry) continue;

    const adapterCap = regEntry.adapter.capability;
    const roles = regEntry.semanticRoles?.join(',') || '';
    
    // Group generic templates into specific cohorts based on their role/capability
    let cohortId = adapterCap;
    if (adapterCap === 'generic_execution_v1') {
      if (roles.includes('static_scene')) {
        cohortId = 'generic_static_scene';
      } else if (roles.includes('text_hook') || roles.includes('explainer_text')) {
        cohortId = 'generic_text';
      } else if (roles.includes('b_roll')) {
        cohortId = 'generic_media';
      } else if (roles.includes('transition')) {
        cohortId = 'generic_transition';
      } else if (roles.includes('visual_effect')) {
        cohortId = 'generic_effect';
      } else if (roles.includes('ui_simulation')) {
        cohortId = 'generic_ui';
      } else {
        cohortId = 'generic_component';
      }
    }

    if (!cohorts[cohortId]) {
      cohorts[cohortId] = {
        cohortId,
        memberTemplates: [],
        executionContract: adapterCap,
        requiredMappings: Object.keys(regEntry.propIntelligence.contentMapping || {}),
        representativeTemplates: [],
        sampleSize: adapterCap === 'generic_execution_v1' ? 3 : 2
      };
    }
    
    cohorts[cohortId].memberTemplates.push(templateId);
  }

  // Select representative templates
  for (const c of Object.values(cohorts)) {
    // Just pick the first few as a deterministic sample
    const sampleSize = Math.min(c.sampleSize, c.memberTemplates.length);
    c.representativeTemplates = c.memberTemplates.slice(0, sampleSize);
    
    // Attempt to grab one from the end as an "edge case" if we have many
    if (c.memberTemplates.length > sampleSize) {
       c.representativeTemplates[sampleSize - 1] = c.memberTemplates[c.memberTemplates.length - 1];
    }
  }

  fs.writeFileSync(COHORTS_OUT, JSON.stringify(Object.values(cohorts), null, 2));
  console.log(`Generated ${Object.keys(cohorts).length} cohorts.`);
}

main();
