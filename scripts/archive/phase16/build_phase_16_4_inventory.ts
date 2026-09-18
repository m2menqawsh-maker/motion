import fs from 'fs';
import path from 'path';

const ROOT_DIR = process.cwd();
const AUDIT_PATH = path.join(ROOT_DIR, 'ground-truth/phase_15_execution_audit.json');
const SCHEMAS_PATH = path.join(ROOT_DIR, 'ground-truth/template_prop_schemas.json');

const audit = JSON.parse(fs.readFileSync(AUDIT_PATH, 'utf8'));
const schemas = JSON.parse(fs.readFileSync(SCHEMAS_PATH, 'utf8'));

const blocked = audit.auditResults.filter((r: any) => 
  r.blocker !== null && 
  r.adapterCapability !== 'social_captions_v1' // exclude the ones we just unlocked
);

const inventory = blocked.map((b: any) => {
  const schema = schemas[b.templateId] || { required: [], optional: [], schema_signature: '' };
  return {
    templateId: b.templateId,
    blocker: b.blocker,
    unresolvedProps: b.unresolvedProps,
    dependencyStatus: b.dependencyStatus,
    assetStatus: b.assetStatus,
    required: schema.required,
    optional: schema.optional,
    schemaSignature: schema.schema_signature
  };
});

fs.writeFileSync(path.join(ROOT_DIR, 'ground-truth/phase_16_4_blocked_inventory.json'), JSON.stringify(inventory, null, 2));

console.log(`Total blocked: ${blocked.length}`);
console.log('Blocker breakdown:');
const counts: any = {};
blocked.forEach((b: any) => {
  counts[b.blocker] = (counts[b.blocker] || 0) + 1;
});
console.table(counts);

// Print templates to stdout for manual analysis
console.log("\nBlocked Templates Details:");
inventory.forEach((i: any) => {
  console.log(`- ${i.templateId} (${i.blocker}):`);
  if (i.unresolvedProps && i.unresolvedProps.length > 0) console.log(`  Unresolved: ${i.unresolvedProps.join(', ')}`);
});
