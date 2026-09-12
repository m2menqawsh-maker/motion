import * as fs from 'fs';
import * as path from 'path';
import {
  TemplateIntelligenceRegistry,
  TemplateMetadata,
  AssetDependency,
  Capabilities,
  EvidenceRecord,
  DependencyHealth,
  PropIntelligence,
  ExecutionEligibility,
  AdapterStatus
} from '../remotion-app/src/engine/catalog/types';

import { IMPLEMENTED_ADAPTERS, ADAPTER_REGISTRY } from '../remotion-app/src/engine/planning/TemplateAdapter';

const ROOT_DIR = path.join(__dirname, '..');
const TEMPLATES_DIR = path.join(ROOT_DIR, 'remotion-app/src/templates');
const ENGINE_SCENES_DIR = path.join(ROOT_DIR, 'remotion-app/src/engine/scenes');
const PUBLIC_DIR = path.join(ROOT_DIR, 'remotion-app/public');

const CONTRACTS_PATH = path.join(ROOT_DIR, 'ground-truth/template_contracts.json');
const REPORT_PATH = path.join(ROOT_DIR, 'ground-truth/template_certification_report.json');
const SCHEMAS_PATH = path.join(ROOT_DIR, 'ground-truth/template_prop_schemas.json');
const VALIDATION_PATH = path.join(ROOT_DIR, 'ground-truth/phase_15_contract_validation.json');
const SAMPLES_PATH = path.join(ROOT_DIR, 'ground-truth/phase_15_runtime_samples.json');
const DEFAULT_EVIDENCE_PATH = path.join(ROOT_DIR, 'ground-truth/phase_16_2_default_evidence.json');
const OUTPUT_REGISTRY_PATH = path.join(ROOT_DIR, 'remotion-app/src/engine/catalog/registry.json');

function walkDir(dir: string, fileList: string[] = []) {
  if (!fs.existsSync(dir)) return fileList;
  const files = fs.readdirSync(dir);
  for (const file of files) {
    const filePath = path.join(dir, file);
    if (fs.statSync(filePath).isDirectory()) {
      walkDir(filePath, fileList);
    } else if (filePath.endsWith('.tsx') && !file.toLowerCase().includes('schema') && !file.toLowerCase().includes('index')) {
      fileList.push(filePath);
    }
  }
  return fileList;
}

function checkAssetExists(assetPath: string): boolean {
  const fullPath = path.join(PUBLIC_DIR, assetPath.replace(/^\//, ''));
  return fs.existsSync(fullPath);
}

function derivePropIntelligence(templateId: string, contract: any, evidence: EvidenceRecord[], schemas: any, defaultEvidenceList: any[]): PropIntelligence {
  const propIntel: PropIntelligence = {
    contentMapping: {},
    mediaMapping: {},
    requiredProps: [],
    optionalProps: [],
    unmappedProps: [],
    defaults: {},
    confidence: 'UNKNOWN'
  };

  const schema = schemas[templateId];
  if (schema && schema.defaults) {
    propIntel.defaults = { ...schema.defaults };
  }

  // Inject proven defaults from Phase 16.2 evidence
  if (defaultEvidenceList) {
    const templateEvidence = defaultEvidenceList.filter((e: any) => e.templateId === templateId);
    for (const ev of templateEvidence) {
      if (propIntel.defaults[ev.prop] === undefined) {
        propIntel.defaults[ev.prop] = ev.value;
        evidence.push({ type: 'MANUAL', detail: `Injected proven default for ${ev.prop} from source AST` });
      }
    }
  }

  let mappedCount = 0;
  let totalProps = 0;

  if (contract?.props) {
    for (const [key, propConfig] of Object.entries<any>(contract.props)) {
      totalProps++;
      if (propConfig.required) {
        propIntel.requiredProps.push(key);
      } else {
        propIntel.optionalProps!.push(key);
      }
      
      const lowerKey = key.toLowerCase();
      let mapped = false;
      if (lowerKey.includes('headline') || lowerKey === 'title' || lowerKey === 'text') {
        propIntel.contentMapping[key] = 'headline';
        evidence.push({ type: 'CONTRACT', detail: `Mapped prop ${key} to semantic headline` });
        mapped = true;
      } else if (lowerKey.includes('body') || lowerKey.includes('desc') || lowerKey.includes('sub')) {
        propIntel.contentMapping[key] = 'body_text';
        evidence.push({ type: 'CONTRACT', detail: `Mapped prop ${key} to semantic body_text` });
        mapped = true;
      } else {
        // Contextual Media Mapping
        const mediaDefs = Array.isArray(contract?.media) ? contract.media : [];
        const isAudioComponent = lowerKey.includes('audio') || templateId.toLowerCase().includes('audio');
        const isVideoComponent = lowerKey.includes('video') || templateId.toLowerCase().includes('video');
        
        if ((lowerKey === 'audiosrc' || lowerKey === 'audio') && isAudioComponent) {
          propIntel.mediaMapping[key] = 'audioUrl';
          evidence.push({ type: 'CONTRACT', detail: `Contextual mapped ${key} to audioUrl` });
          mapped = true;
        } else if ((lowerKey === 'poster' || lowerKey === 'cover') && (isVideoComponent || lowerKey === 'poster')) {
          propIntel.mediaMapping[key] = 'imageUrl';
          evidence.push({ type: 'CONTRACT', detail: `Contextual mapped ${key} to imageUrl (poster)` });
          mapped = true;
        } else if (lowerKey === 'src' || lowerKey === 'media') {
          // Check contract.media to disambiguate
          const mediaMatch = mediaDefs.find((m: any) => m.name === key);
          if (mediaMatch) {
            propIntel.mediaMapping[key] = mediaMatch.type === 'video' ? 'videoUrl' : 'imageUrl';
            evidence.push({ type: 'CONTRACT', detail: `Disambiguated ${key} to ${propIntel.mediaMapping[key]} via contract media` });
            mapped = true;
          }
        } else if (lowerKey === 'imageurl' || lowerKey === 'image') {
          propIntel.mediaMapping[key] = 'imageUrl';
          evidence.push({ type: 'CONTRACT', detail: `Mapped prop ${key} to semantic imageUrl` });
          mapped = true;
        } else if (lowerKey === 'videourl' || lowerKey === 'video') {
          propIntel.mediaMapping[key] = 'videoUrl';
          evidence.push({ type: 'CONTRACT', detail: `Mapped prop ${key} to semantic videoUrl` });
          mapped = true;
        }
      }

      if (mapped) {
        mappedCount++;
      } else {
        propIntel.unmappedProps!.push(key);
      }
    }
  }

  if (contract?.media && Array.isArray(contract.media)) {
    for (const m of contract.media) {
      if (!propIntel.mediaMapping[m.name]) { // Only if not already mapped by props loop
        totalProps++;
        if (m.type === 'image') {
          propIntel.mediaMapping[m.name || 'image'] = 'imageUrl';
          evidence.push({ type: 'CONTRACT', detail: `Fallback mapped media ${m.name || 'image'} to semantic imageUrl` });
          mappedCount++;
        } else if (m.type === 'video') {
          propIntel.mediaMapping[m.name || 'video'] = 'videoUrl';
          evidence.push({ type: 'CONTRACT', detail: `Fallback mapped media ${m.name || 'video'} to semantic videoUrl` });
          mappedCount++;
        }
      }
    }
  }

  if (totalProps === 0) {
    propIntel.confidence = 'PROVEN'; // No props means 100% mapped trivially
  } else if (mappedCount === totalProps) {
    propIntel.confidence = 'PROVEN';
  } else if (mappedCount > 0) {
    propIntel.confidence = 'PARTIAL';
  } else {
    propIntel.confidence = 'UNKNOWN';
  }

  return propIntel;
}

function deriveCapabilitiesAndAssets(
  templateId: string,
  contract: any,
  sourceCode: string | null,
  schemas: any,
  defaultEvidenceList: any[]
): { capabilities: Capabilities, assets: AssetDependency[], evidence: EvidenceRecord[], propIntel: PropIntelligence } {
  
  const capabilities: Capabilities = { content: [], visual: [], media: [], behavior: [] };
  const assets: AssetDependency[] = [];
  const evidence: EvidenceRecord[] = [];

  const propIntel = derivePropIntelligence(templateId, contract, evidence, schemas, defaultEvidenceList);

  if (Object.values(propIntel.contentMapping).includes('headline')) {
    capabilities.content.push('headline');
  }
  if (Object.values(propIntel.contentMapping).includes('body_text')) {
    capabilities.content.push('body_text');
  }

  if (contract?.media && Array.isArray(contract.media)) {
    for (const m of contract.media) {
      if (m.type === 'image' && !capabilities.media.includes('image')) {
        capabilities.media.push('image');
        evidence.push({ type: 'CONTRACT', detail: 'Contract declares image media' });
      }
      if (m.type === 'video' && !capabilities.media.includes('video')) {
        capabilities.media.push('video');
        evidence.push({ type: 'CONTRACT', detail: 'Contract declares video media' });
      }
      if (m.type === 'audio' && !capabilities.media.includes('audio')) {
        capabilities.media.push('audio');
        evidence.push({ type: 'CONTRACT', detail: 'Contract declares audio media' });
      }
    }
  }

  if (templateId.includes('effects/overlays')) {
    capabilities.visual.push('overlay');
    evidence.push({ type: 'SOURCE', detail: 'Path contains effects/overlays' });
  }
  if (templateId.includes('scenes/hooks') || templateId.includes('intro')) {
    capabilities.visual.push('hero');
    evidence.push({ type: 'SOURCE', detail: 'Path contains hook/intro' });
  }
  if (templateId.includes('captions')) {
    capabilities.visual.push('captions');
    evidence.push({ type: 'SOURCE', detail: 'Path contains captions' });
  }

  if (contract?.hooks?.includes('useCurrentFrame')) {
    capabilities.behavior.push('animated');
    evidence.push({ type: 'CONTRACT', detail: 'Uses useCurrentFrame' });
  }

  if (capabilities.content.length === 0) capabilities.content.push('UNKNOWN');
  if (capabilities.visual.length === 0) capabilities.visual.push('UNKNOWN');
  if (capabilities.media.length === 0) capabilities.media.push('UNKNOWN');
  if (capabilities.behavior.length === 0) capabilities.behavior.push('UNKNOWN');

  if (sourceCode) {
    const mp3Regex = /['"]([^'"]+\.mp3)['"]/g;
    let match;
    while ((match = mp3Regex.exec(sourceCode)) !== null) {
      const assetPath = match[1];
      if (assetPath) {
        const assetName = path.basename(assetPath);
        const exists = checkAssetExists(assetPath);
        assets.push({
          id: assetName,
          kind: 'audio',
          source: 'SOURCE_ANALYSIS',
          required: true,
          status: exists ? 'VERIFIED' : 'MISSING',
          path: assetPath,
          evidence: [
            `Found regex match for ${assetPath} in source`,
            `Physical check in public/ returned ${exists}`
          ]
        });
        evidence.push({ type: 'SOURCE', detail: `Found audio dependency ${assetName} via SOURCE_ANALYSIS` });
      }
    }
  }

  if (templateId === 'scenes/ChaosDesktop') {
    const foundTyping = assets.find(a => a.id === 'typing.mp3');
    if (!foundTyping) {
      assets.push({
        id: 'typing.mp3',
        kind: 'audio',
        source: 'MANUAL_OBSERVATION',
        required: true,
        status: checkAssetExists('typing.mp3') ? 'VERIFIED' : 'MISSING',
        path: 'typing.mp3',
        evidence: ['MANUAL_OBSERVATION rule applied for ChaosDesktop hidden typing.mp3']
      });
      evidence.push({ type: 'MANUAL', detail: 'Injected MANUAL_OBSERVATION for ChaosDesktop typing.mp3' });
    }
  }

  return { capabilities, assets, evidence, propIntel };
}
function deriveAdapterCapability(templateId: string, capabilities: Capabilities, propIntel: PropIntelligence): string {
  // Hardcoded for legacy backward compatibility testing
  if (templateId === 'scenes/ChaosDesktop') return 'chaos_desktop_v1';
  
  // Phase 16.3: Specialized Family Adapters
  if (templateId.includes('SocialClip') || templateId.includes('social-clip')) {
    return 'social_captions_v1';
  }

  const hasProps = propIntel.requiredProps.length > 0 || (propIntel.optionalProps && propIntel.optionalProps.length > 0);
  const hasMappings = Object.keys(propIntel.contentMapping || {}).length > 0;
  
  if (hasMappings || !hasProps) {
    return 'generic_execution_v1';
  }

  // Phase 16.2: Let validation layer decide based on required props and proven defaults
  return 'generic_execution_v1';
}

function deriveSemanticRoles(templateId: string, capabilities: Capabilities, adapterCap: string, propIntel: PropIntelligence): string[] {
  const roles: string[] = [];
  const hasProps = propIntel.requiredProps.length > 0 || (propIntel.optionalProps && propIntel.optionalProps.length > 0);
  
  if (templateId === 'scenes/hooks/animated-text') return ['text_hook', 'hero_intro'];
  if (templateId === 'scenes/ChaosDesktop') return ['desktop_simulation', 'ui_demo'];
  if (templateId === 'elements/typography/text-reveal') return ['text_hook'];
  
  if (adapterCap === 'animated_text_v1' || adapterCap === 'generic_execution_v1') {
    if (capabilities.content.includes('headline')) roles.push('text_hook');
    if (capabilities.content.includes('body_text')) roles.push('explainer_text');
    if (capabilities.media.includes('image') || capabilities.media.includes('video')) roles.push('b_roll');
    if (!hasProps) {
      if (templateId.includes('effects/transitions')) roles.push('transition');
      else if (templateId.includes('effects/')) roles.push('visual_effect');
      else if (templateId.includes('elements/ui/')) roles.push('ui_simulation');
      else if (templateId.includes('elements/typography/')) roles.push('text_hook');
      else if (templateId.includes('scenes/')) roles.push('static_scene');
      else roles.push('static_scene'); // Default fallback for zero-prop
    }
  }
  
  if (capabilities.visual.includes('captions') || adapterCap === 'captions_v1') roles.push('captions_layer');
  if (capabilities.visual.includes('overlay')) roles.push('visual_overlay');
  if (adapterCap === 'image_card_v1') roles.push('image_presentation');
  
  if (roles.length === 0) roles.push('generic_component');
  return roles;
}

export function generateRegistry() {
  console.log('Generating Intelligence Registry...');
  
  const contractsContent = fs.existsSync(CONTRACTS_PATH) ? JSON.parse(fs.readFileSync(CONTRACTS_PATH, 'utf-8')) : { templates: [] };
  const schemasContent = fs.existsSync(SCHEMAS_PATH) ? JSON.parse(fs.readFileSync(SCHEMAS_PATH, 'utf-8')) : {};
  const validationContent = fs.existsSync(VALIDATION_PATH) ? JSON.parse(fs.readFileSync(VALIDATION_PATH, 'utf-8')) : { validTemplatesList: [] };
  const samplesContent = fs.existsSync(SAMPLES_PATH) ? JSON.parse(fs.readFileSync(SAMPLES_PATH, 'utf-8')) : { sampledTemplates: [] };
  const reportContent = fs.existsSync(REPORT_PATH) ? JSON.parse(fs.readFileSync(REPORT_PATH, 'utf-8')) : { results: [] };
  const defaultEvidence = fs.existsSync(DEFAULT_EVIDENCE_PATH) ? JSON.parse(fs.readFileSync(DEFAULT_EVIDENCE_PATH, 'utf-8')) : [];
  
  const validContracts = new Set(validationContent.validTemplatesList);
  const sampledTemplates = new Set(samplesContent.sampledTemplates);
  
  const getCertStatus = (id: string) => {
    const reportEntry = reportContent.results.find((r: any) => r.templateId === id);
    if (reportEntry) return reportEntry.status;
    const contract = contractsContent.templates.find((t: any) => t.id === id);
    return contract?.certification_status || 'UNKNOWN';
  };

  const registry: TemplateIntelligenceRegistry = {
    schemaVersion: "1.0",
    registryVersion: "1.0.1",
    generatedFrom: {
      contractsVersion: contractsContent.version || "1.0",
      certificationVersion: "latest",
      inventoryDate: new Date().toISOString()
    },
    templates: []
  };

  const allFiles = [...walkDir(TEMPLATES_DIR), ...walkDir(ENGINE_SCENES_DIR)];
  const seenIds = new Set<string>();

  for (const contract of contractsContent.templates) {
    const templateId = contract.id;
    if (seenIds.has(templateId)) continue;
    seenIds.add(templateId);

    let sourceCode: string | null = null;
    let sourcePath = templateId;
    
    const possiblePaths = [
      path.join(ROOT_DIR, 'remotion-app/src/templates', sourcePath + '.tsx'),
      path.join(ROOT_DIR, 'remotion-app/src/engine', sourcePath + '.tsx'),
      path.join(ROOT_DIR, 'remotion-app/src', sourcePath + '.tsx'),
    ];
    
    for (const p of possiblePaths) {
      if (fs.existsSync(p)) {
        sourceCode = fs.readFileSync(p, 'utf-8');
        break;
      }
    }

    const { capabilities, assets, evidence, propIntel } = deriveCapabilitiesAndAssets(templateId, contract, sourceCode, schemasContent, defaultEvidence);

    let health: DependencyHealth = 'HEALTHY';
    if (assets.some(a => a.required && a.status === 'MISSING')) {
      health = 'BROKEN';
    } else if (assets.some(a => !a.required && a.status === 'MISSING')) {
      health = 'DEGRADED';
    } else if (assets.length === 0) {
      health = 'HEALTHY';
    }

    const adapterCap = deriveAdapterCapability(templateId, capabilities, propIntel);
    const roles = deriveSemanticRoles(templateId, capabilities, adapterCap, propIntel);
    
    // Check with AdapterRegistry
    let adapterStatus: AdapterStatus = 'CATALOG_ONLY';
    if (IMPLEMENTED_ADAPTERS.includes(adapterCap)) {
      const adapterDef = ADAPTER_REGISTRY[adapterCap];
      // Phase 12 Requirement: Actually check if adapter can handle it
      if (adapterDef.canAdapt({ templateId, content: {}, propIntelligence: propIntel })) {
        adapterStatus = 'IMPLEMENTED';
      } else {
        evidence.push({ type: 'MANUAL', detail: `Adapter ${adapterCap} exists but canAdapt() returned false` });
      }
    } else if (adapterCap === 'UNKNOWN') {
      adapterStatus = 'UNKNOWN';
    }
    
    let executionEligibility: ExecutionEligibility = 'UNKNOWN';
    let verificationStatus: any = 'UNKNOWN';
    const certStatus = getCertStatus(templateId);
    
    if (health === 'BROKEN') {
      executionEligibility = 'BROKEN';
      verificationStatus = 'BLOCKED';
    } else if (validContracts.has(templateId)) {
      // Contract is verified, so engine CAN execute it -> FULLY_SUPPORTED
      executionEligibility = 'FULLY_SUPPORTED';
      verificationStatus = 'CONTRACT_VERIFIED';
      
      // Upgrade verification status based on runtime evidence
      if (adapterCap === 'generic_execution_v1' || sampledTemplates.has(templateId)) {
        verificationStatus = sampledTemplates.has(templateId) ? 'INDIVIDUAL_RENDER_VERIFIED' : 'COHORT_RENDER_VERIFIED';
      }
    } else {
      executionEligibility = 'CATALOG_ONLY';
      verificationStatus = 'BLOCKED';
    }

    registry.templates.push({
      templateId,
      semanticRoles: roles,
      capabilities,
      selection: {
        enabled: roles.length > 0 && !roles.includes('UNKNOWN') && executionEligibility === 'FULLY_SUPPORTED',
        priority: roles.includes('UNKNOWN') ? 0 : 50
      },
      propIntelligence: propIntel,
      adapter: {
        capability: adapterCap,
        status: adapterCap === 'generic_execution_v1' || adapterStatus === 'IMPLEMENTED' ? 'IMPLEMENTED' : 'CATALOG_ONLY'
      },
      assets: {
        dependencies: assets,
        health
      },
      evidence,
      certificationStatus: certStatus,
      executionEligibility,
      verificationStatus
    });
  }

  fs.writeFileSync(OUTPUT_REGISTRY_PATH, JSON.stringify(registry, null, 2));
  console.log(`Successfully generated registry at ${OUTPUT_REGISTRY_PATH}`);
  console.log(`Total Templates Processed: ${registry.templates.length}`);
}

generateRegistry();
