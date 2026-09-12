import * as fs from 'fs';
import * as path from 'path';

const pluginRoot = path.resolve(__dirname, '../../');
const matrixPath = path.join(pluginRoot, 'template_intelligence_matrix.json');
const outPath = path.join(pluginRoot, 'ground-truth/phase_14_baseline.json');

async function main() {
  const matrix = JSON.parse(fs.readFileSync(matrixPath, 'utf-8'));
  
  const stats = {
    timestamp: new Date().toISOString(),
    totalTemplates: matrix.length,
    executionEligibility: {
      fullySupported: 0,
      catalogOnly: 0,
      broken: 0
    },
    adapters: {
      implemented: 0,
      missing: 0
    },
    certification: {
      certified: 0,
      notCertified: 0
    }
  };

  for (const t of matrix) {
    if (t.executionEligibility === 'FULLY_SUPPORTED') stats.executionEligibility.fullySupported++;
    else if (t.executionEligibility === 'CATALOG_ONLY') stats.executionEligibility.catalogOnly++;
    else if (t.executionEligibility === 'BROKEN') stats.executionEligibility.broken++;

    if (t.adapterStatus === 'IMPLEMENTED') stats.adapters.implemented++;
    else stats.adapters.missing++;

    if (t.certification === 'CERTIFIED') stats.certification.certified++;
    else stats.certification.notCertified++;
  }

  fs.writeFileSync(outPath, JSON.stringify(stats, null, 2));
  console.log(`Phase 14 baseline created at ${outPath}`);
  console.log(JSON.stringify(stats, null, 2));
}

main().catch(console.error);
