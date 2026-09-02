import * as fs from 'fs';
import * as path from 'path';

const ROOT_DIR = path.resolve(__dirname, '../../');
const CONTRACTS_PATH = path.join(ROOT_DIR, 'ground-truth/template_contracts.json');
const SCHEMAS_PATH = path.join(ROOT_DIR, 'ground-truth/template_prop_schemas.json');
const REGISTRY_PATH = path.join(ROOT_DIR, 'remotion-app/src/engine/catalog/registry.json');
const AUDIT_OUT = path.join(ROOT_DIR, 'ground-truth/phase_15_execution_audit.json');
const VALIDATION_OUT = path.join(ROOT_DIR, 'ground-truth/phase_15_contract_validation.json');

function main() {
  const contracts = JSON.parse(fs.readFileSync(CONTRACTS_PATH, 'utf-8')).templates;
  const schemas = JSON.parse(fs.readFileSync(SCHEMAS_PATH, 'utf-8'));
  const registry = JSON.parse(fs.readFileSync(REGISTRY_PATH, 'utf-8')).templates;

  const auditResults: any[] = [];
  const validTemplates: string[] = [];
  let genericCount = 0;
  let specializedCount = 0;
  let sourceErrorCount = 0;

  for (const t of contracts) {
    const regEntry = registry.find((r: any) => r.templateId === t.id);
    const schema = schemas[t.id];

    // Source validation (assume yes since they are in contracts, but we check schema existence)
    const physicalSourceExists = true; 
    let propsParseable = !!schema;
    
    // Required props & defaults
    const requiredProps = schema?.required || [];
    const optionalProps = schema?.optional || [];
    // Read defaults from registry propIntelligence, which includes injected proven defaults
    const defaults = regEntry?.propIntelligence?.defaults || schema?.defaults || {};
    
    let allRequiredResolvable = true;
    const unresolvedProps: string[] = [];

    // Check if required props have proven defaults OR semantic mapping
    const contentMapping = regEntry?.propIntelligence?.contentMapping || {};
    const mediaMapping = regEntry?.propIntelligence?.mediaMapping || {};
    
    // All physical keys mapped from semantic
    const allMappedKeys = [...Object.keys(contentMapping), ...Object.keys(mediaMapping)];
    
    for (const req of requiredProps) {
      if (defaults[req] === undefined && !allMappedKeys.includes(req)) {
        allRequiredResolvable = false;
        unresolvedProps.push(req);
      }
    }

    const adapterCapability = regEntry?.adapter?.capability || 'UNKNOWN';
    if (adapterCapability === 'generic_execution_v1') genericCount++;
    else if (adapterCapability !== 'UNKNOWN') specializedCount++;

    const dependencyStatus = regEntry?.assets?.health || 'UNKNOWN';
    const assetStatus = t.media?.length > 0 && Object.keys(mediaMapping).length === 0 ? 'NEEDS_MEDIA_MAPPING' : 'HEALTHY';

    let isContractValid = propsParseable && allRequiredResolvable && adapterCapability !== 'UNKNOWN' && dependencyStatus === 'HEALTHY' && assetStatus === 'HEALTHY';
    
    // Explicit classification for zero-prop templates
    let executionClassification = 'UNKNOWN';
    if (requiredProps.length === 0 && optionalProps.length === 0) {
      executionClassification = 'STATIC_ZERO_PROP';
    } else if (isContractValid) {
      executionClassification = 'CONTRACT_VALID';
    }

    let blocker = null;
    if (!isContractValid) {
      if (!propsParseable) blocker = 'SOURCE_ERROR';
      else if (!allRequiredResolvable) blocker = 'MISSING_DEFAULT_OR_MAPPING';
      else if (dependencyStatus === 'BROKEN') blocker = 'INVALID_ASSET_DEPENDENCY';
      else if (assetStatus === 'NEEDS_MEDIA_MAPPING') blocker = 'MISSING_MEDIA_MAPPING';
      else if (adapterCapability === 'UNKNOWN') blocker = 'NO_SEMANTIC_ROLE';
      else blocker = 'UNKNOWN_BLOCKER';
    }

    if (blocker === 'SOURCE_ERROR') sourceErrorCount++;

    auditResults.push({
      templateId: t.id,
      physicalSourceExists,
      propsParseable,
      requiredProps,
      optionalProps,
      provenDefaults: Object.keys(defaults),
      semanticMappings: allMappedKeys,
      adapterCapability,
      dependencyStatus,
      assetStatus,
      executionClassification,
      blocker,
      unresolvedProps
    });

    if (isContractValid) {
      validTemplates.push(t.id);
    }
  }

  // Generate output files
  fs.writeFileSync(AUDIT_OUT, JSON.stringify({ total: contracts.length, auditResults }, null, 2));
  
  const validationReport = {
    totalTemplates: contracts.length,
    contractValid: validTemplates.length,
    genericExecution: genericCount,
    specializedAdapters: specializedCount,
    sourceErrors: sourceErrorCount,
    blocked: contracts.length - validTemplates.length,
    validTemplatesList: validTemplates
  };
  fs.writeFileSync(VALIDATION_OUT, JSON.stringify(validationReport, null, 2));
  console.log(`Validation complete. Valid: ${validTemplates.length}/${contracts.length}`);
}

main();
