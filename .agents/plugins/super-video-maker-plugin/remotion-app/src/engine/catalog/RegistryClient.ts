import * as fs from 'fs';
import * as path from 'path';
import { TemplateIntelligenceRegistry, TemplateMetadata } from './types';

const ROOT_DIR = path.join(__dirname, '../../../../');
const REGISTRY_PATH = path.join(__dirname, 'registry.json');
const CONTRACTS_PATH = path.join(ROOT_DIR, 'ground-truth/template_contracts.json');
const REPORT_PATH = path.join(ROOT_DIR, 'ground-truth/template_certification_report.json');

export class RegistryValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'RegistryValidationError';
  }
}

export class RegistryClient {
  private static registryData: TemplateIntelligenceRegistry | null = null;
  private static contractsData: any = null;
  private static reportData: any = null;

  public static __setTestingData(registry: any, contracts: any, reports: any) {
    this.registryData = registry;
    this.contractsData = contracts;
    this.reportData = reports;
  }

  public static __clearTestingData() {
    this.registryData = null;
    this.contractsData = null;
    this.reportData = null;
  }

  public static loadCatalogs() {
    if (!this.registryData) {
      if (!fs.existsSync(REGISTRY_PATH)) {
        throw new RegistryValidationError(`Registry file not found at ${REGISTRY_PATH}`);
      }
      this.registryData = JSON.parse(fs.readFileSync(REGISTRY_PATH, 'utf-8'));
    }

    if (!this.contractsData) {
      if (fs.existsSync(CONTRACTS_PATH)) {
        this.contractsData = JSON.parse(fs.readFileSync(CONTRACTS_PATH, 'utf-8'));
      } else {
        this.contractsData = { templates: [] };
      }
    }

    if (!this.reportData) {
      if (fs.existsSync(REPORT_PATH)) {
        this.reportData = JSON.parse(fs.readFileSync(REPORT_PATH, 'utf-8'));
      } else {
        this.reportData = { results: [] };
      }
    }

    this.validateRegistry();
  }

  private static validateRegistry() {
    const registry = this.registryData!;
    if (registry.schemaVersion !== '1.0') {
      throw new RegistryValidationError(`Unsupported schema version: ${registry.schemaVersion}`);
    }
    if (!registry.registryVersion) {
      throw new RegistryValidationError(`Missing registryVersion`);
    }

    const templateIds = new Set<string>();
    const knownTemplates = new Set<string>();

    for (const contract of this.contractsData.templates || []) {
      knownTemplates.add(contract.id);
    }
    for (const result of this.reportData.results || []) {
      knownTemplates.add(result.templateId);
    }

    for (const template of registry.templates) {
      if (templateIds.has(template.templateId)) {
        throw new RegistryValidationError(`Duplicate template ID in registry: ${template.templateId}`);
      }
      templateIds.add(template.templateId);

      if (!knownTemplates.has(template.templateId)) {
        throw new RegistryValidationError(`Template does not exist in the authoritative template contract/certification universe: ${template.templateId}`);
      }

      if (!template.semanticRoles || !Array.isArray(template.semanticRoles)) {
        throw new RegistryValidationError(`Invalid semanticRoles for template: ${template.templateId}`);
      }

      if (typeof template.selection?.enabled !== 'boolean') {
        throw new RegistryValidationError(`Invalid selection.enabled for template: ${template.templateId}`);
      }
      if (typeof template.selection?.priority !== 'number') {
        throw new RegistryValidationError(`Invalid selection.priority for template: ${template.templateId}`);
      }

      if (!template.adapter?.capability) {
        throw new RegistryValidationError(`Missing adapter capability for template: ${template.templateId}`);
      }

      if (template.assets?.dependencies) {
        const depIds = new Set<string>();
        for (const dep of template.assets.dependencies) {
          if (depIds.has(dep.id)) {
            throw new RegistryValidationError(`Duplicate dependency ID ${dep.id} in template: ${template.templateId}`);
          }
          depIds.add(dep.id);
        }
      }
    }
  }

  public static getCertificationStatus(templateId: string): string {
    const reportEntry = this.reportData?.results?.find((r: any) => r.templateId === templateId);
    if (reportEntry) {
      return reportEntry.status;
    }
    const contract = this.contractsData?.templates?.find((t: any) => t.id === templateId);
    return contract?.certification_status || 'UNKNOWN';
  }

  public static findTemplates(criteria: {
    role: string;
    requiredCapabilities?: {
      content?: string[];
      visual?: string[];
      media?: string[];
      behavior?: string[];
    };
    preferredCapabilities?: {
      content?: string[];
      visual?: string[];
      media?: string[];
      behavior?: string[];
    };
    requireExecutable?: boolean;
  }): TemplateMetadata[] {
    this.loadCatalogs();

    const candidates = this.registryData!.templates.filter(t => t.semanticRoles.includes(criteria.role));
    
    // We map to clone the objects because we dynamically recalculate eligibility
    const clonedCandidates = candidates.map(t => ({ ...t }));

    const eligible = clonedCandidates.filter(t => {
      if (!t.selection.enabled) return false;
      
      const certStatus = this.getCertificationStatus(t.templateId);
      
      if (t.assets.health === 'BROKEN') {
        t.executionEligibility = 'BROKEN';
      } else if (certStatus !== 'CERTIFIED' && certStatus !== 'VALIDATED') {
        t.executionEligibility = 'CATALOG_ONLY';
      } else if (t.adapter.status !== 'IMPLEMENTED') {
        t.executionEligibility = 'CATALOG_ONLY';
      } else {
        t.executionEligibility = 'FULLY_SUPPORTED';
      }

      if (criteria.requireExecutable && t.executionEligibility !== 'FULLY_SUPPORTED') return false;

      if (criteria.requiredCapabilities) {
        if (criteria.requiredCapabilities.content) {
          if (!criteria.requiredCapabilities.content.every(c => t.capabilities?.content?.includes(c))) return false;
        }
        if (criteria.requiredCapabilities.visual) {
          if (!criteria.requiredCapabilities.visual.every(c => t.capabilities?.visual?.includes(c))) return false;
        }
        if (criteria.requiredCapabilities.media) {
          if (!criteria.requiredCapabilities.media.every(c => t.capabilities?.media?.includes(c))) return false;
        }
        if (criteria.requiredCapabilities.behavior) {
          if (!criteria.requiredCapabilities.behavior.every(c => t.capabilities?.behavior?.includes(c))) return false;
        }
      }

      return true;
    });

    eligible.sort((a, b) => {
      const aCert = this.getCertificationStatus(a.templateId);
      const bCert = this.getCertificationStatus(b.templateId);
      const aScore = (aCert === 'CERTIFIED' || aCert === 'VALIDATED') ? 2 : 1;
      const bScore = (bCert === 'CERTIFIED' || bCert === 'VALIDATED') ? 2 : 1;
      
      if (aScore !== bScore) return bScore - aScore;

      const aHealth = a.assets.health === 'HEALTHY' ? 3 : (a.assets.health === 'DEGRADED' ? 2 : 1);
      const bHealth = b.assets.health === 'HEALTHY' ? 3 : (b.assets.health === 'DEGRADED' ? 2 : 1);
      if (aHealth !== bHealth) return bHealth - aHealth;

      const aAdapter = a.adapter.status === 'IMPLEMENTED' ? 2 : 1;
      const bAdapter = b.adapter.status === 'IMPLEMENTED' ? 2 : 1;
      if (aAdapter !== bAdapter) return bAdapter - aAdapter;

      // preferred capabilities overlap
      if (criteria.preferredCapabilities) {
        const scorePref = (t: TemplateMetadata) => {
          let s = 0;
          if (criteria.preferredCapabilities?.content) s += criteria.preferredCapabilities.content.filter(c => t.capabilities.content.includes(c)).length;
          if (criteria.preferredCapabilities?.visual) s += criteria.preferredCapabilities.visual.filter(c => t.capabilities.visual.includes(c)).length;
          return s;
        };
        const aPref = scorePref(a);
        const bPref = scorePref(b);
        if (aPref !== bPref) return bPref - aPref;
      }

      if (a.selection.priority !== b.selection.priority) {
        return b.selection.priority - a.selection.priority;
      }

      return a.templateId.localeCompare(b.templateId);
    });

    return eligible;
  }
}
