import fs from 'fs';
import path from 'path';

const ROOT_DIR = process.cwd();

const auditPath = path.join(ROOT_DIR, 'ground-truth/phase_15_execution_audit.json');
const registryPath = path.join(ROOT_DIR, 'remotion-app/src/engine/catalog/registry.json');
const schemaPath = path.join(ROOT_DIR, 'ground-truth/template_prop_schemas.json');

const audit = JSON.parse(fs.readFileSync(auditPath, 'utf8'));
const registry = JSON.parse(fs.readFileSync(registryPath, 'utf8'));
const schemas = JSON.parse(fs.readFileSync(schemaPath, 'utf8'));

const blockedTemplates = audit.auditResults.filter((r: any) => 
  r.executionClassification !== 'CONTRACT_VALID' && 
  r.executionClassification !== 'STATIC_ZERO_PROP'
);

const inventory = blockedTemplates.map((b: any) => {
  const regEntry = registry.templates.find((t: any) => t.templateId === b.templateId);
  const schemaEntry = schemas[b.templateId] || {};
  
  // Try to heuristically determine the family based on ID and required props
  let family = 'unknown';
  let classification = 'singleton';
  
  if (b.templateId.toLowerCase().includes('social') || b.templateId.toLowerCase().includes('clip')) {
    family = 'social_captions_v1';
    classification = 'family';
  } else if (b.templateId.includes('app-ui')) {
    family = 'app_ui_v1';
    classification = 'family';
  }

  return {
    templateId: b.templateId,
    sourcePath: `remotion-app/src/templates/${b.templateId}.tsx`,
    semanticRoles: regEntry?.semanticRoles || [],
    requiredProps: b.requiredProps,
    optionalProps: b.optionalProps,
    unmappedProps: b.unresolvedProps, // These are unresolved!
    structuralPropSignatures: b.requiredProps.filter((p: string) => !b.semanticMappings.includes(p)), // naive approach
    mediaRequirements: regEntry?.capabilities?.media || [],
    currentBlocker: b.blocker,
    existingProvenDefaults: b.provenDefaults,
    potentialFamily: family,
    classification: classification,
    estimatedAdapterComplexity: classification === 'family' ? 'MEDIUM' : 'HIGH',
    semanticSourceRequired: 'CreativeSpec (varies)'
  };
});

// Deterministic Ranking
inventory.sort((a: any, b: any) => {
  // Families first
  if (a.classification === 'family' && b.classification !== 'family') return -1;
  if (a.classification !== 'family' && b.classification === 'family') return 1;
  
  // Social captions over app-ui (due to phase instructions)
  if (a.potentialFamily === 'social_captions_v1' && b.potentialFamily !== 'social_captions_v1') return -1;
  if (a.potentialFamily !== 'social_captions_v1' && b.potentialFamily === 'social_captions_v1') return 1;
  
  return a.templateId.localeCompare(b.templateId);
});

fs.writeFileSync(
  path.join(ROOT_DIR, 'ground-truth/phase_16_3_blocked_inventory.json'),
  JSON.stringify(inventory, null, 2)
);

console.log(`Inventory generated with ${inventory.length} blocked templates.`);
