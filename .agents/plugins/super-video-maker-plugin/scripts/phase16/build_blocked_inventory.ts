import * as fs from 'fs';
import * as path from 'path';

const ROOT_DIR = path.resolve(__dirname, '../../');
const REGISTRY_PATH = path.join(ROOT_DIR, 'remotion-app/src/engine/catalog/registry.json');
const SCHEMAS_PATH = path.join(ROOT_DIR, 'ground-truth/template_prop_schemas.json');
const OUTPUT_PATH = path.join(ROOT_DIR, 'ground-truth/phase_16_1_blocked_inventory.json');

function main() {
  const registry = JSON.parse(fs.readFileSync(REGISTRY_PATH, 'utf-8')).templates;
  const schemas = JSON.parse(fs.readFileSync(SCHEMAS_PATH, 'utf-8'));
  
  const blockedInventory = [];

  for (const t of registry) {
    if (t.verificationStatus !== 'BLOCKED' && t.executionEligibility !== 'CATALOG_ONLY' && t.executionEligibility !== 'BROKEN') {
      continue;
    }
    
    // Determine blocker reason
    let blocker = 'UNKNOWN';
    if (t.assets.health === 'BROKEN') {
      blocker = 'MISSING_DEPENDENCIES';
    } else if (!t.semanticRoles || t.semanticRoles.length === 0 || t.semanticRoles.includes('UNKNOWN')) {
      blocker = 'NO_SEMANTIC_ROLE';
    } else if (t.propIntelligence.unmappedProps.length > 0) {
      blocker = 'MISSING_DEFAULT_OR_MAPPING';
    } else if (t.capabilities.media.length > 0 && Object.keys(t.propIntelligence.mediaMapping).length === 0) {
      blocker = 'MISSING_MEDIA_MAPPING';
    }

    const sourcePath = path.join(ROOT_DIR, `remotion-app/src/templates/${t.templateId}.tsx`);
    let sourceStr = '';
    if (fs.existsSync(sourcePath)) {
      sourceStr = fs.readFileSync(sourcePath, 'utf-8');
    } else {
      // maybe in engine/
      const enginePath = path.join(ROOT_DIR, `remotion-app/src/engine/${t.templateId}.tsx`);
      if (fs.existsSync(enginePath)) sourceStr = fs.readFileSync(enginePath, 'utf-8');
    }
    
    const getPropType = (propName) => {
      if (!sourceStr) return 'unknown';
      // First try Zod syntax
      const zRegex = new RegExp(`${propName}\\s*:\\s*z\\.(\\w+)\\s*\\(`);
      const zMatch = sourceStr.match(zRegex);
      if (zMatch) return zMatch[1];
      
      const zRegex2 = new RegExp(`${propName}\\s*:\\s*z\\.(\\w+)\\s*\\.`);
      const zMatch2 = sourceStr.match(zRegex2);
      if (zMatch2) return zMatch2[1];
      
      // Try TypeScript type interface / type alias
      // e.g. propName?: string[] or propName: SomeType[] or propName: { ... }
      const tsRegex = new RegExp(`${propName}\\s*\\??\\s*:\\s*([^;,\n]+)`);
      const tsMatch = sourceStr.match(tsRegex);
      if (tsMatch) {
        let t = tsMatch[1].trim();
        if (t.includes('[]') || t.startsWith('Array<')) return 'array';
        if (t.startsWith('{') || t.startsWith('Record<')) return 'object';
        if (t.includes('string')) return 'string';
        if (t.includes('number')) return 'number';
        if (t.includes('boolean')) return 'boolean';
      }
      
      return 'unknown';
    };

    const enhanceProps = (props) => {
      return props.map(p => ({
        name: p,
        type: getPropType(p)
      }));
    };
    
    const pi = t.propIntelligence;
    
    blockedInventory.push({
      templateId: t.templateId,
      executionEligibility: t.executionEligibility,
      verificationStatus: t.verificationStatus,
      blocker,
      requiredProps: enhanceProps(pi.requiredProps || []),
      optionalProps: enhanceProps(pi.optionalProps || []),
      unmappedProps: enhanceProps(pi.unmappedProps || []),
      defaults: pi.defaults || {},
      semanticRoles: t.semanticRoles || [],
      contentMapping: pi.contentMapping || {},
      mediaRequirements: t.capabilities.media || [],
      assetHealth: t.assets.health,
      sourcePath: `remotion-app/src/templates/${t.templateId}.tsx`,
      adapterCapability: t.adapter.capability,
      category: t.templateId.split('/')[0] // rough category
    });
  }

  console.log(`Found ${blockedInventory.length} blocked templates.`);
  fs.writeFileSync(OUTPUT_PATH, JSON.stringify(blockedInventory, null, 2));
}

main();
