import { AdapterDefinition } from './types';
import { social_captions_v1 } from './families/social_captions_v1';

export const ADAPTER_REGISTRY: Record<string, AdapterDefinition> = {
  'social_captions_v1': social_captions_v1,
  'animated_text_v1': {
    capability: 'animated_text_v1',
    version: '1.0',
    requiredSemanticInputs: ['headline'],
    canAdapt: (context) => {
      // Must have mapped physical text prop
      return Object.keys(context.propIntelligence.contentMapping).length > 0;
    },
    adapt: (context) => {
      // The SemanticContentResolver already prepared the physical props.
      const optional = context.propIntelligence.optionalProps || [];
      const overrides: Record<string, any> = {};
      
      if (optional.includes('entrance_direction')) {
        overrides['entrance_direction'] = 'up';
      }
      if (optional.includes('camera_track')) {
        overrides['camera_track'] = 'zoom_in';
      }

      return {
        props: {
          ...context.content,
          ...overrides
        }
      };
    }
  },
  'chaos_desktop_v1': {
    capability: 'chaos_desktop_v1',
    version: '1.0',
    requiredSemanticInputs: [],
    canAdapt: () => true,
    adapt: (context) => {
      return { props: {} };
    }
  },
  'generic_execution_v1': {
    capability: 'generic_execution_v1',
    version: '1.0',
    requiredSemanticInputs: [],
    canAdapt: (context) => {
      // Can adapt if we have at least one mapped semantic field OR if it requires zero props
      const hasProps = context.propIntelligence.requiredProps.length > 0 || (context.propIntelligence.optionalProps && context.propIntelligence.optionalProps.length > 0);
      const hasMappings = Object.keys(context.propIntelligence.contentMapping || {}).length > 0;
      return hasMappings || !hasProps;
    },
    adapt: (context) => {
      // SemanticContentResolver already mapped semantic inputs to physical props using contentMapping.
      // So the physical props are already inside context.content. We just pass them through.
      return {
        props: {
          ...context.content
        }
      };
    }
  }
};

export const IMPLEMENTED_ADAPTERS = Object.keys(ADAPTER_REGISTRY);
