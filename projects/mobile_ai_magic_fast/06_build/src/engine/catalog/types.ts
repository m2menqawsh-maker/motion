export type AssetDependencySource =
  | 'CONTRACT_DECLARED'
  | 'SOURCE_ANALYSIS'
  | 'MANUAL_OBSERVATION'
  | 'UNKNOWN';

export type AssetDependencyStatus = 'VERIFIED' | 'MISSING' | 'UNDECLARED' | 'UNKNOWN';

export interface AssetDependency {
  id: string;
  kind: string; // 'audio', 'image', 'video', 'other'
  source: AssetDependencySource;
  required: boolean;
  status: AssetDependencyStatus;
  path?: string;
  evidence: string[];
}

export type DependencyHealth = 'HEALTHY' | 'DEGRADED' | 'BROKEN' | 'UNKNOWN';

export interface Capabilities {
  content: string[];
  visual: string[];
  media: string[];
  behavior: string[];
}

export interface SelectionMetadata {
  enabled: boolean;
  priority: number;
}

export type ExecutionEligibility = 'FULLY_SUPPORTED' | 'PARTIALLY_SUPPORTED' | 'CATALOG_ONLY' | 'BROKEN' | 'UNKNOWN';
export type VerificationStatus = 'CONTRACT_VERIFIED' | 'COHORT_RENDER_VERIFIED' | 'INDIVIDUAL_RENDER_VERIFIED' | 'BLOCKED' | 'UNKNOWN';
export type AdapterStatus = 'IMPLEMENTED' | 'CATALOG_ONLY' | 'UNKNOWN';

export interface PropIntelligence {
  contentMapping: Record<string, string>;
  mediaMapping: Record<string, string>;
  requiredProps: string[];
  optionalProps?: string[];
  unmappedProps?: string[];
  defaults?: Record<string, any>;
  confidence?: 'PROVEN' | 'PARTIAL' | 'UNKNOWN';
}

export interface AdapterCapability {
  capability: string;
  status: AdapterStatus;
}

export interface EvidenceRecord {
  type: 'CONTRACT' | 'SOURCE' | 'MANUAL' | 'CERTIFICATION' | 'INVENTORY';
  detail: string;
}

export interface TemplateMetadata {
  templateId: string;
  semanticRoles: string[];
  capabilities: Capabilities;
  selection: SelectionMetadata;
  propIntelligence: PropIntelligence;
  adapter: AdapterCapability;
  assets: {
    dependencies: AssetDependency[];
    health: DependencyHealth;
  };
  evidence: EvidenceRecord[];
  certificationStatus: string;
  executionEligibility: ExecutionEligibility;
  verificationStatus: VerificationStatus;
  executionBlocker?: string;
}

export interface TemplateIntelligenceRegistry {
  schemaVersion: string;
  registryVersion: string;
  generatedFrom: {
    contractsVersion: string;
    certificationVersion: string;
    inventoryDate: string;
  };
  templates: TemplateMetadata[];
}

