import * as fs from 'fs';
import * as path from 'path';

const ROOT_DIR = path.resolve(__dirname, '../../');
const CONTRACTS_PATH = path.join(ROOT_DIR, 'ground-truth/template_contracts.json');
const SCHEMAS_PATH = path.join(ROOT_DIR, 'ground-truth/template_prop_schemas.json');
const OUTPUT_PATH = path.join(ROOT_DIR, 'ground-truth/phase_14_execution_bridge_audit.json');
const TEMPLATES_DIR = path.join(ROOT_DIR, 'remotion-app/src');
const ENGINE_DIR = path.join(ROOT_DIR, 'remotion-app/src/engine/scenes');

function readSource(templatePath: string): string | null {
  const p1 = path.join(TEMPLATES_DIR, templatePath);
  if (fs.existsSync(p1)) return fs.readFileSync(p1, 'utf-8');
  const p2 = path.join(ENGINE_DIR, templatePath.split('/').pop() || '');
  if (fs.existsSync(p2)) return fs.readFileSync(p2, 'utf-8');
  return null;
}

function classifyBlocker(t: any, schema: any, source: string | null): string {
  if (t.certification_status === 'PASS' && t.executionEligibility === 'FULLY_SUPPORTED') {
    return 'ALREADY_EXECUTABLE';
  }
  
  // If it's certified but not fully supported, it might be CERTIFICATION_ONLY (or no adapter maps it yet)
  if (t.certification_status === 'PASS') {
    return 'CERTIFICATION_ONLY';
  }

  // Look at props and semantic
  const hasProps = Object.keys(t.props || {}).length > 0 || (schema && (schema.required?.length > 0 || schema.optional?.length > 0));
  
  if (hasProps && !schema) {
    return 'NO_PROP_MAPPING';
  }

  if (schema && schema.required && schema.required.length > 0) {
    const hasDefaultsForRequired = schema.required.every((r: string) => schema.defaults && schema.defaults[r] !== undefined);
    if (!hasDefaultsForRequired) {
      // It has required props but no defaults, and no generic adapter mapping covers it
      return 'NO_DEFAULT_RESOLUTION';
    }
  }

  if (t.dependencies && t.dependencies.some((d: any) => d.status === 'MISSING')) {
    return 'NO_DEPENDENCY_RESOLUTION';
  }

  if (t.media && t.media.length > 0) {
    return 'NO_ASSET_RESOLUTION';
  }

  // Default fallback for catalog templates that lack semantic routing
  return 'NO_SEMANTIC_ROLE';
}

function main() {
  const contracts = JSON.parse(fs.readFileSync(CONTRACTS_PATH, 'utf-8')).templates;
  const schemas = JSON.parse(fs.readFileSync(SCHEMAS_PATH, 'utf-8'));

  const categories: Record<string, any[]> = {
    typography: [],
    media: [],
    ui: [],
    effects: [],
    scenes: []
  };

  for (const t of contracts) {
    if (t.id.includes('typography')) categories.typography.push(t);
    else if (t.id.includes('media') || t.id.includes('image') || t.id.includes('video')) categories.media.push(t);
    else if (t.id.includes('ui') || t.id.includes('primitives/app-ui')) categories.ui.push(t);
    else if (t.id.includes('effects') || t.id.includes('transitions')) categories.effects.push(t);
    else if (t.id.includes('scenes') || t.id.includes('compositions')) categories.scenes.push(t);
  }

  const sample: any[] = [];
  const selectedIds = new Set<string>();

  for (const [cat, items] of Object.entries(categories)) {
    let count = 0;
    for (const t of items) {
      if (count >= 10) break;
      if (selectedIds.has(t.id)) continue;
      
      const source = readSource(t.path);
      const schema = schemas[t.id];
      const blocker = classifyBlocker(t, schema, source);
      
      sample.push({
        templateId: t.id,
        category: cat,
        blocker,
        hasSource: !!source,
        hasSchema: !!schema,
        props: schema ? { required: schema.required, optional: schema.optional, defaults: schema.defaults } : t.props
      });
      selectedIds.add(t.id);
      count++;
    }
  }

  fs.writeFileSync(OUTPUT_PATH, JSON.stringify({ sampleSize: sample.length, results: sample }, null, 2));
  console.log(`Audit complete. Extracted ${sample.length} templates. Output saved to ${OUTPUT_PATH}`);
}

main();
