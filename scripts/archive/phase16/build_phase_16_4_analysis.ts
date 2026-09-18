import fs from 'fs';
import path from 'path';

const ROOT_DIR = process.cwd();
const INVENTORY_PATH = path.join(ROOT_DIR, 'ground-truth/phase_16_4_blocked_inventory.json');

const inventory = JSON.parse(fs.readFileSync(INVENTORY_PATH, 'utf8'));

// Filter out the orphans
const validInventory = inventory.filter((i: any) => !i.templateId.includes('orphan'));

const strategy: any = {
  "Compositional Wrappers (Require children)": {
    description: "These templates require React elements (children) as props. They are internal composable primitives, not standalone scenes. They cannot be executed generically via JSON without a specialized layout orchestration adapter.",
    templates: [],
    recommendedAction: "Leave as CATALOG_ONLY (Internal Primitives) or build a mega Layout Adapter."
  },
  "Scalar UI Primitives (Generic Fix Opportunity)": {
    description: "These templates only require simple scalar props (label, name, value, to). They were blocked because the semantic generic mapper didn't know how to map CreativeSpec's headline/body_text to them.",
    templates: [],
    recommendedAction: "Generic Fix (Update SemanticContentResolver to map headline -> label/name/value/to)."
  },
  "Complex Data UI (Specialized Families)": {
    description: "These templates require arrays of complex objects (items, messages, columns, actions, keyframes). They can be grouped into an App UI Simulation family.",
    templates: [],
    recommendedAction: "Build a specialized family adapter (e.g. app_ui_simulation_v1)."
  },
  "Media Mapping Blockers (Generic Fix Opportunity)": {
    description: "Templates blocked by MISSING_MEDIA_MAPPING. They require media assets but lack semantic mapping.",
    templates: [],
    recommendedAction: "Generic Fix (Map asset requirements to CreativeSpec media slots)."
  },
  "Dependency Blockers": {
    description: "Templates blocked by missing physical dependencies (e.g., missing video files).",
    templates: [],
    recommendedAction: "Fix physical dependency in assets."
  },
  "True Singletons": {
    description: "Templates with highly unique structural requirements (orchestrators).",
    templates: [],
    recommendedAction: "Build specialized singleton adapters or leave as CATALOG_ONLY."
  }
};

let genericFixes = 0;
let familyPotential = 0;
let trueSingletons = 0;
let depBlockers = 0;

validInventory.forEach((item: any) => {
  if (item.blocker === 'INVALID_ASSET_DEPENDENCY') {
    strategy["Dependency Blockers"].templates.push(item.templateId);
    depBlockers++;
  } else if (item.blocker === 'MISSING_MEDIA_MAPPING') {
    strategy["Media Mapping Blockers (Generic Fix Opportunity)"].templates.push(item.templateId);
    genericFixes++;
  } else if (item.unresolvedProps?.includes('children')) {
    strategy["Compositional Wrappers (Require children)"].templates.push(item.templateId);
    trueSingletons++; // Counted as un-executable singletons
  } else if (['name', 'label', 'value', 'to'].some(prop => item.unresolvedProps?.includes(prop))) {
    strategy["Scalar UI Primitives (Generic Fix Opportunity)"].templates.push(item.templateId);
    genericFixes++;
  } else if (['items', 'messages', 'columns', 'tabs', 'actions', 'keyframes'].some(prop => item.unresolvedProps?.includes(prop))) {
    strategy["Complex Data UI (Specialized Families)"].templates.push(item.templateId);
    familyPotential++;
  } else {
    strategy["True Singletons"].templates.push(item.templateId);
    trueSingletons++;
  }
});

fs.writeFileSync(path.join(ROOT_DIR, 'ground-truth/phase_16_4_adapter_strategy.json'), JSON.stringify(strategy, null, 2));

const coverage = {
  currentFullySupported: 129, // 127 + 2 social clips
  totalCatalog: 153, // actually 158 total, 153 processed
  blockedAnalyzed: validInventory.length,
  potentialCoverage: {
    afterGenericFixes: 129 + genericFixes,
    afterFamilies: 129 + genericFixes + familyPotential,
    afterDependencyFixes: 129 + genericFixes + familyPotential + depBlockers
  }
};

fs.writeFileSync(path.join(ROOT_DIR, 'ground-truth/phase_16_4_coverage_projection.json'), JSON.stringify(coverage, null, 2));

console.log("Analysis complete.");
