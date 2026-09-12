import * as fs from 'fs';
import * as path from 'path';

const ROOT_DIR = path.join(__dirname, '..');
const REGISTRY_PATH = path.join(ROOT_DIR, 'remotion-app/src/engine/catalog/registry.json');
const REPORT_PATH = path.join(ROOT_DIR, 'ground-truth/template_certification_report.json');
const OUTPUT_PATH = path.join(ROOT_DIR, 'template_intelligence_matrix.json');

function generateMatrix() {
  if (!fs.existsSync(REGISTRY_PATH)) {
    console.error('Registry not found.');
    process.exit(1);
  }

  const registry = JSON.parse(fs.readFileSync(REGISTRY_PATH, 'utf-8'));
  const reportData = fs.existsSync(REPORT_PATH) ? JSON.parse(fs.readFileSync(REPORT_PATH, 'utf-8')) : { results: [] };

  const matrix = registry.templates.map((t: any) => {
    const reportEntry = reportData.results.find((r: any) => r.templateId === t.templateId);
    const certification = reportEntry ? reportEntry.status : 'UNKNOWN';

    return {
      templateId: t.templateId,
      certification,
      dependencyHealth: t.assets.health,
      semanticRoles: t.semanticRoles,
      capabilities: t.capabilities,
      adapterCapability: t.adapter.capability,
      adapterStatus: t.adapter.status,
      propRequirements: t.propIntelligence.requiredProps,
      mediaRequirements: Object.keys(t.propIntelligence.mediaMapping),
      evidenceCount: t.evidence.length,
      executionEligibility: t.executionEligibility,
      propConfidence: t.propIntelligence.confidence || 'UNKNOWN',
      familyConfidence: (t.adapter.capability !== 'UNKNOWN') ? 'PROVEN' : 'UNKNOWN',
      blockingReasons: buildBlockingReasons(t)
    };
  });

  fs.writeFileSync(OUTPUT_PATH, JSON.stringify(matrix, null, 2));
  console.log(`Generated Intelligence Matrix with ${matrix.length} templates at ${OUTPUT_PATH}`);
}

function buildBlockingReasons(t: any): string[] {
  const reasons = [];
  if (t.assets.health === 'BROKEN') reasons.push('Missing required dependencies');
  if (t.adapter.status !== 'IMPLEMENTED') reasons.push('Adapter is not implemented');
  if (t.executionEligibility === 'CATALOG_ONLY' && t.adapter.status === 'IMPLEMENTED') reasons.push('Not certified');
  return reasons;
}

generateMatrix();
