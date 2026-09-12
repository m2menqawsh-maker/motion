import { validateTemplateProps } from '../contract/validator';
import { BuildPlanScene, ValidationError } from './types';

export function resolveProps(scene: BuildPlanScene): {
  errors: ValidationError[];
  warnings: ValidationError[];
} {
  const result = validateTemplateProps(scene.spec.templateId, scene.spec.props || {});
  
  const errors: ValidationError[] = [];
  const warnings: ValidationError[] = [];

  for (const e of result.errors) {
    const errorObj: ValidationError = {
      code: e.failureType,
      stage: 'PROPS_GATE',
      templateId: scene.spec.templateId,
      prop: e.propName,
      message: `Expected: ${e.expected}, Got: ${e.received}. ${e.possibleResolution}`,
      severity: e.severity,
    };

    if (e.severity === 'ERROR') {
      errors.push(errorObj);
    } else {
      warnings.push(errorObj);
    }
  }

  // Update scene with safe props
  scene.normalizedProps = result.safeProps;

  return { errors, warnings };
}
