import * as fs from 'fs';
import * as path from 'path';

const pluginRoot = path.resolve(__dirname, '../../');
const groundTruthDir = path.join(pluginRoot, 'ground-truth');
const matrixPath = path.join(pluginRoot, 'template_intelligence_matrix.json');
const candidatesPath = path.join(pluginRoot, 'adapter_family_candidates.json');
const outPath = path.join(groundTruthDir, 'phase_13_baseline.json');

async function main() {
  if (!fs.existsSync(matrixPath)) {
    console.error(`Matrix not found at ${matrixPath}`);
    process.exit(1);
  }

  const matrixRaw = fs.readFileSync(matrixPath, 'utf-8');
  const matrix = JSON.parse(matrixRaw);

  let totalTemplates = matrix.length;
  let fullySupported = 0;
  let partiallySupported = 0;
  let catalogOnly = 0;
  let broken = 0;
  let unknown = 0;
  let blockedByAssets = 0;
  let blockedByCertification = 0;
  let blockedByProps = 0;
  let blockedByAdapter = 0;

  for (const t of matrix) {
    if (t.executionEligibility === 'FULLY_SUPPORTED') fullySupported++;
    else if (t.executionEligibility === 'PARTIALLY_SUPPORTED') partiallySupported++;
    else if (t.executionEligibility === 'CATALOG_ONLY') catalogOnly++;
    else if (t.executionEligibility === 'BROKEN') broken++;
    else unknown++;

    if (t.blockingReasons && t.blockingReasons.length > 0) {
      const reasons = t.blockingReasons.join(' ');
      if (reasons.includes('dependency') || reasons.includes('Asset')) blockedByAssets++;
      if (reasons.includes('ertification')) blockedByCertification++;
      if (reasons.includes('prop') || reasons.includes('Prop')) blockedByProps++;
      if (reasons.includes('Adapter') || reasons.includes('adapter')) blockedByAdapter++;
    }
  }

  const candidatesRaw = fs.existsSync(candidatesPath) ? fs.readFileSync(candidatesPath, 'utf-8') : '[]';
  const candidates = JSON.parse(candidatesRaw);
  
  const adapterFamilies: Record<string, number> = {};
  let highConfidenceCandidates = 0;

  for (const c of candidates) {
    if (c.candidateFamilies && c.candidateFamilies.length > 0) {
      for (const fam of c.candidateFamilies) {
        adapterFamilies[fam] = (adapterFamilies[fam] || 0) + 1;
      }
    }
    if (c.confidence === 'PROVEN') {
      highConfidenceCandidates++;
    }
  }

  const baseline = {
    timestamp: new Date().toISOString(),
    totalTemplates,
    executionEligibility: {
      fullySupported,
      partiallySupported,
      catalogOnly,
      broken,
      unknown
    },
    blockers: {
      blockedByAssets,
      blockedByCertification,
      blockedByProps,
      blockedByAdapter
    },
    candidates: {
      highConfidenceCandidates,
      adapterFamilies
    }
  };

  fs.writeFileSync(outPath, JSON.stringify(baseline, null, 2));
  console.log(`Baseline created at ${outPath}`);
  console.log(JSON.stringify(baseline, null, 2));
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
