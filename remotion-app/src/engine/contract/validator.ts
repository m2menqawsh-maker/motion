import contractsData from '../../../../ground-truth/template_contracts.json';

export type ValidationSeverity = 'ERROR' | 'WARNING';

export interface ValidationError {
  templateId: string;
  propName?: string;
  expected?: string;
  received?: string;
  failureType: string;
  severity: ValidationSeverity;
  possibleResolution: string;
}

export interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
  safeProps: any;
}

export function validateTemplateProps(templateId: string, inputProps: any): ValidationResult {
  const template = contractsData.templates.find((t: any) => t.id === templateId);
  const errors: ValidationError[] = [];
  let safeProps = { ...inputProps };

  if (!template) {
    return {
      valid: false,
      errors: [{
        templateId,
        failureType: 'CONTRACT_MISSING',
        severity: 'ERROR',
        possibleResolution: 'Check if the template ID is correct and cataloged.'
      }],
      safeProps: {}
    };
  }

  if (template.certification_status === 'BLOCKED') {
    errors.push({
      templateId,
      failureType: 'CONTRACT_BLOCKED',
      severity: 'ERROR',
      possibleResolution: 'This template cannot be safely instantiated.'
    });
  }

  // Check required props
  for (const [propName, propDef] of Object.entries(template.props || {})) {
    const p = propDef as any;
    const value = inputProps[propName];

    if (p.required && (value === undefined || value === null)) {
      errors.push({
        templateId,
        propName,
        expected: p.type,
        received: 'undefined',
        failureType: 'MISSING_REQUIRED_PROP',
        severity: 'ERROR',
        possibleResolution: 'Provide the required property.'
      });
      continue;
    }

    if (value !== undefined && value !== null) {
      // Type validation
      if (p.is_array) {
        if (!Array.isArray(value)) {
          errors.push({
            templateId,
            propName,
            expected: 'array',
            received: typeof value,
            failureType: 'INVALID_ARRAY',
            severity: 'ERROR',
            possibleResolution: 'Ensure the property is an array.'
          });
        }
      } else if (p.type.includes('number')) {
        const num = Number(value);
        if (isNaN(num)) {
          errors.push({
            templateId,
            propName,
            expected: 'number',
            received: 'NaN',
            failureType: 'INVALID_NUMBER',
            severity: 'ERROR',
            possibleResolution: 'Provide a valid number.'
          });
        } else if (!isFinite(num)) {
          errors.push({
            templateId,
            propName,
            expected: 'finite number',
            received: 'Infinity',
            failureType: 'INVALID_NUMBER',
            severity: 'ERROR',
            possibleResolution: 'Provide a finite number.'
          });
        } else if (propName.toLowerCase().includes('duration') && num < 0) {
          errors.push({
            templateId,
            propName,
            expected: 'positive number',
            received: String(num),
            failureType: 'INVALID_TIMING',
            severity: 'ERROR',
            possibleResolution: 'Duration must be positive.'
          });
        }
      }
    } else if (p.default !== 'UNKNOWN' && p.default !== undefined) {
       // Safe Resolution using explicit default
       try {
           safeProps[propName] = JSON.parse(p.default);
       } catch (e) {
           safeProps[propName] = p.default;
       }
    }
  }

  // Media Safety
  if (template.media && template.media.length > 0) {
    // In a real browser environment, checking file existence synchronously is impossible.
    // However, we can validate paths don't contain unsafe absolute paths.
    for (const m of template.media) {
       // We don't necessarily know the prop name if it was UNKNOWN, but we can scan props for string paths
       for (const [propName, value] of Object.entries(inputProps)) {
          if (typeof value === 'string' && (value.includes('C:/') || value.includes('C:\\\\'))) {
             errors.push({
                templateId,
                propName,
                expected: 'relative or staticFile path',
                received: 'absolute windows path',
                failureType: 'INVALID_MEDIA',
                severity: 'ERROR',
                possibleResolution: 'Use staticFile() or relative paths.'
             });
          }
       }
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    safeProps: errors.length === 0 ? safeProps : {}
  };
}
