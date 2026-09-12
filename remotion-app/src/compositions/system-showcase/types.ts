export interface TemplateMeta {
  id: string;
  name: string;
  type: 'scene' | 'element' | 'effect' | 'engine' | 'misc';
  family: string;
  quality: 'A' | 'B' | 'C';
  status: string;
  rtl_ready: boolean;
  source: string;
  path: string;
  use_cases: string[];
  intents: string[];
  moods: string[];
  capabilities: string[];
  notes?: string;
}

export interface ShowcaseItem {
  meta: TemplateMeta;
  component?: React.ComponentType<any>;
  mockProps?: Record<string, any>;
  isUtility?: boolean;
  isAvailable?: boolean;
  failureReason?: string;
}
