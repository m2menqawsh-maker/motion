import * as fs from 'fs';
import * as path from 'path';

const ROOT_DIR = path.resolve(__dirname, '../../');
const FAMILIES_PATH = path.join(ROOT_DIR, 'ground-truth/phase_16_1_adapter_families.json');
const OUTPUT_STRATEGY = path.join(ROOT_DIR, 'ground-truth/phase_16_1_adapter_strategy.json');

function main() {
  const familiesData = JSON.parse(fs.readFileSync(FAMILIES_PATH, 'utf-8'));
  
  let {
    adapterFamilies,
    singletonCandidates,
    genericMappingCandidates,
    defaultFixCandidates,
    dependencyBlockers,
    unresolved
  } = familiesData;
  
  // Rank adapter families by leverage
  // Priority: 1. Coverage, 2. Structural similarity (few props), 3. Low complexity, 4. High confidence
  adapterFamilies.sort((a: any, b: any) => {
    // 1. Coverage
    if (b.memberCount !== a.memberCount) return b.memberCount - a.memberCount;
    // 2. Low complexity
    const complexityRank = { 'LOW': 3, 'MEDIUM': 2, 'HIGH': 1 };
    if (complexityRank[b.complexity] !== complexityRank[a.complexity]) {
      return complexityRank[b.complexity] - complexityRank[a.complexity];
    }
    // 3. Confidence
    const confidenceRank = { 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1 };
    if (confidenceRank[b.confidence] !== confidenceRank[a.confidence]) {
      return confidenceRank[b.confidence] - confidenceRank[a.confidence];
    }
    return 0;
  });
  
  // Clean up strategy output
  const strategy = {
    totalBlocked: 49,
    adapterFamilies: adapterFamilies,
    singletonCandidates,
    genericMappingCandidates,
    defaultFixCandidates,
    dependencyBlockers,
    unresolved,
    minimumPracticalAdapterCount: adapterFamilies.length,
    potentialCoverageGain: adapterFamilies.reduce((acc: number, f: any) => acc + f.estimatedCoverageGain, 0) + genericMappingCandidates.length + defaultFixCandidates.length
  };
  
  fs.writeFileSync(OUTPUT_STRATEGY, JSON.stringify(strategy, null, 2));
  
  console.log(`Ranked ${adapterFamilies.length} adapter families.`);
  console.log(`Potential Coverage Gain: +${strategy.potentialCoverageGain}`);
}

main();
