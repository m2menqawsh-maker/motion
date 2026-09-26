import * as fs from 'fs';
import * as path from 'path';

const ROOT_DIR = path.resolve(__dirname, '../../');
const CANDIDATES_PATH = path.join(ROOT_DIR, 'adapter_family_candidates.json');
const OUT_PATH = path.join(ROOT_DIR, 'ground-truth/phase_14_family_priorities.json');

function prioritize() {
  const candidates = JSON.parse(fs.readFileSync(CANDIDATES_PATH, 'utf-8'));
  const familyStats: Record<string, { count: number; highConfidence: number; templates: string[] }> = {};

  for (const t of candidates) {
    for (const f of t.candidateFamilies) {
      if (!familyStats[f]) {
        familyStats[f] = { count: 0, highConfidence: 0, templates: [] };
      }
      familyStats[f].count++;
      familyStats[f].templates.push(t.templateId);
      if (t.confidence === 'HIGH') {
        familyStats[f].highConfidence++;
      }
    }
  }

  const priorities = Object.entries(familyStats)
    .map(([family, stats]) => ({
      family,
      candidateCount: stats.count,
      highConfidenceCount: stats.highConfidence,
      score: (stats.count * 0.5) + (stats.highConfidence * 1.5),
      representativeTemplates: stats.templates.slice(0, 5)
    }))
    .sort((a, b) => b.score - a.score);

  fs.writeFileSync(OUT_PATH, JSON.stringify(priorities, null, 2));
  console.log(`Priorities generated at ${OUT_PATH}`);
  console.log(JSON.stringify(priorities, null, 2));
}

prioritize();
