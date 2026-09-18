import * as fs from 'fs';
import * as path from 'path';

const pluginRoot = path.resolve(__dirname, '../../');
const groundTruthDir = path.join(pluginRoot, 'ground-truth');
const matrixPath = path.join(pluginRoot, 'template_intelligence_matrix.json');
const candidatesPath = path.join(pluginRoot, 'adapter_family_candidates.json');
const outPath = path.join(groundTruthDir, 'phase_13_family_priorities.json');

const IMPLEMENTED_ADAPTERS = ['animated_text_v1', 'chaos_desktop_v1'];

async function main() {
  const matrixRaw = fs.readFileSync(matrixPath, 'utf-8');
  const matrix: any[] = JSON.parse(matrixRaw);
  const matrixMap = new Map<string, any>();
  matrix.forEach(m => matrixMap.set(m.templateId, m));

  const candidatesRaw = fs.readFileSync(candidatesPath, 'utf-8');
  const candidates: any[] = JSON.parse(candidatesRaw);

  const families = new Map<string, any>();

  for (const candidate of candidates) {
    if (!candidate.candidateFamilies || candidate.candidateFamilies.length === 0) continue;

    const intel = matrixMap.get(candidate.templateId);
    if (!intel) continue;
    if (intel.executionEligibility === 'FULLY_SUPPORTED') continue; // Already supported

    for (const fam of candidate.candidateFamilies) {
      if (!families.has(fam)) {
        families.set(fam, {
          family: fam,
          candidateCount: 0,
          highConfidence: 0,
          healthyAssets: 0,
          propCompatible: 0,
          existingReusability: IMPLEMENTED_ADAPTERS.includes(fam),
          templates: []
        });
      }

      const f = families.get(fam);
      f.candidateCount++;
      f.templates.push(candidate.templateId);

      if (candidate.confidence === 'PROVEN') f.highConfidence++;
      if (intel.dependencyHealth === 'HEALTHY' || intel.dependencyHealth === 'NO_DEPENDENCIES') f.healthyAssets++;
      if (intel.propConfidence === 'PROVEN') f.propCompatible++;
    }
  }

  const priorities = Array.from(families.values()).map(f => {
    // Basic scoring
    let score = f.candidateCount * 10;
    score += f.highConfidence * 20;
    score += f.healthyAssets * 30;
    score += f.propCompatible * 20;
    if (f.existingReusability) score += 100;

    return {
      ...f,
      score,
      priority: score > 200 ? 'HIGH' : score > 100 ? 'MEDIUM' : 'LOW'
    };
  });

  priorities.sort((a, b) => b.score - a.score);

  fs.writeFileSync(outPath, JSON.stringify(priorities, null, 2));
  console.log(`Priorities created at ${outPath}`);
  console.log(JSON.stringify(priorities.slice(0, 3), null, 2));
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
