import { PropIntelligence } from '../../catalog/types';

export interface AdapterContext {
  templateId: string;
  content: Record<string, unknown>;
  propIntelligence: PropIntelligence;
}

export interface AdapterResult {
  props: Record<string, unknown>;
}

export interface AdapterDefinition {
  capability: string;
  version: string;
  requiredSemanticInputs: string[];

  canAdapt(context: AdapterContext): boolean;
  adapt(context: AdapterContext): AdapterResult;
}
