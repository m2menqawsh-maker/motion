import { CompilationError } from './types';
import { TemplateMetadata } from '../catalog/types';
import { ADAPTER_REGISTRY } from './adapters/AdapterRegistry';
import { SemanticContentResolver } from './SemanticContentResolver';

// Re-export for scripts
export { IMPLEMENTED_ADAPTERS, ADAPTER_REGISTRY } from './adapters/AdapterRegistry';

function resolveTemplateProps(
  template: TemplateMetadata,
  adapterProps: Record<string, any>
): { finalProps?: Record<string, any>; error?: string } {
  const finalProps = { ...adapterProps };
  const { propIntelligence } = template;
  const defaults = propIntelligence.defaults || {};

  // Apply schema defaults if not provided by adapter
  for (const [key, defValue] of Object.entries(defaults)) {
    if (finalProps[key] === undefined) {
      finalProps[key] = defValue;
    }
  }

  // Check required props
  const missingProps: string[] = [];
  for (const reqProp of propIntelligence.requiredProps) {
    // If the component defines defaultProps for it, Zod schema might still say required, but usually schema has default or optional.
    // If it's truly required and missing, report it.
    if (finalProps[reqProp] === undefined) {
      missingProps.push(reqProp);
    }
  }

  if (missingProps.length > 0) {
    return { error: `Missing required props: ${missingProps.join(', ')}. No proven default available.` };
  }

  return { finalProps };
}

export function adaptProps(
  role: string,
  template: TemplateMetadata,
  content: Record<string, any> | undefined
): { result?: Record<string, any>; error?: CompilationError } {
  const capability = template.adapter.capability;
  const adapterDef = ADAPTER_REGISTRY[capability];
  
  if (!adapterDef) {
    return {
      error: {
        role,
        message: `Adapter capability "${capability}" is not implemented.`,
      },
    };
  }

  // Phase 12: Semantic Content Resolution
  const { resolvedContent, error: resolveError } = SemanticContentResolver.resolve(
    role,
    content,
    adapterDef,
    template.propIntelligence
  );

  if (resolveError) {
    return { error: resolveError };
  }

  const context = {
    templateId: template.templateId,
    content: resolvedContent!,
    propIntelligence: template.propIntelligence
  };

  if (!adapterDef.canAdapt(context)) {
    return {
      error: {
        role,
        message: `Adapter capability "${capability}" rejected template "${template.templateId}" because it lacks required props or mappings.`,
      },
    };
  }

  try {
    const { props } = adapterDef.adapt(context);
    
    // Resolve defaults and validate required props
    const { finalProps, error: resolvePropsError } = resolveTemplateProps(template, props);
    if (resolvePropsError) {
      return {
        error: {
          role,
          message: `Template "${template.templateId}" failed prop resolution: ${resolvePropsError}`,
        }
      };
    }
    
    return { result: finalProps };
  } catch (err: any) {
    return {
      error: {
        role,
        message: `Template adapter for capability "${capability}" failed: ${err.message}`,
      },
    };
  }
}

