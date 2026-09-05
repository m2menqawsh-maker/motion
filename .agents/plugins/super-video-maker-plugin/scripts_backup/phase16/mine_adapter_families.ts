import * as fs from 'fs';
import * as path from 'path';

const ROOT_DIR = path.resolve(__dirname, '../../');
const INVENTORY_PATH = path.join(ROOT_DIR, 'ground-truth/phase_16_1_blocked_inventory.json');
const OUTPUT_FAMILIES = path.join(ROOT_DIR, 'ground-truth/phase_16_1_adapter_families.json');

function main() {
  const inventory = JSON.parse(fs.readFileSync(INVENTORY_PATH, 'utf-8'));
  
  const clusters = new Map();
  const dependencyBlockers = [];
  const genericMappingCandidates = [];
  const defaultFixCandidates = [];
  const unresolved = [];
  
  for (const t of inventory) {
    if (t.blocker === 'MISSING_DEPENDENCIES') {
      dependencyBlockers.push(t.templateId);
      continue;
    }
    
    // Determine if structural
    const structuralProps = t.unmappedProps.filter((p: any) => p.type === 'array' || p.type === 'object');
    const isStructural = structuralProps.length > 0;
    
    if (t.blocker === 'NO_SEMANTIC_ROLE') {
      genericMappingCandidates.push(t.templateId);
      continue;
    }

    if (t.blocker === 'MISSING_MEDIA_MAPPING' && !isStructural) {
      genericMappingCandidates.push(t.templateId);
      continue;
    }
    
    if (t.blocker === 'MISSING_DEFAULT_OR_MAPPING' && !isStructural) {
      // If it has no structural props, it doesn't need a specialized adapter family
      defaultFixCandidates.push(t.templateId);
      continue;
    }

    // For structural templates, we cluster by the structural props
    const sigArray = structuralProps.map((p: any) => `${p.name}:${p.type}`).sort();
    const signature = sigArray.length > 0 ? sigArray.join(',') : 'UNKNOWN_STRUCTURAL';
    
    if (!clusters.has(signature)) {
      clusters.set(signature, {
        signature,
        props: structuralProps,
        members: []
      });
    }
    
    clusters.get(signature).members.push(t.templateId);
  }
  
  const adapterFamilies = [];
  const singletonCandidates = [];
  let familyCounter = 1;
  
  for (const [sig, cluster] of clusters.entries()) {
    if (cluster.members.length === 1) {
      singletonCandidates.push(cluster.members[0]);
    } else {
      // Determine complexity
      const hasArrays = cluster.props.some((p: any) => p.type === 'array');
      let complexity = 'LOW';
      if (hasArrays) complexity = 'MEDIUM';
      if (cluster.props.length > 3) complexity = 'HIGH';
      
      adapterFamilies.push({
        familyId: `family_v1_${familyCounter++}`,
        memberCount: cluster.members.length,
        members: cluster.members,
        physicalSignature: cluster.props,
        semanticRole: 'UNKNOWN', // to be determined
        requiredTransformations: [],
        sharedProps: cluster.props,
        variableProps: [],
        structuralDifferences: [],
        confidence: cluster.members.length > 2 ? 'HIGH' : 'MEDIUM',
        adapterRequired: true,
        estimatedCoverageGain: cluster.members.length,
        complexity
      });
    }
  }
  
  // Sort families by leverage
  adapterFamilies.sort((a, b) => b.memberCount - a.memberCount);
  
  fs.writeFileSync(OUTPUT_FAMILIES, JSON.stringify({
    adapterFamilies,
    singletonCandidates,
    genericMappingCandidates,
    defaultFixCandidates,
    dependencyBlockers,
    unresolved
  }, null, 2));
  
  console.log(`Clustering complete.`);
  console.log(`Families found: ${adapterFamilies.length}`);
  console.log(`Singletons: ${singletonCandidates.length}`);
}

main();
