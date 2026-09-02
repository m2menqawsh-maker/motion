import React from 'react';
import { validateTemplateProps } from './validator';

export const TemplateAdapter: React.FC<{ templateId: string; props: any; registry: Record<string, React.FC<any>> }> = ({ templateId, props, registry }) => {
  const result = validateTemplateProps(templateId, props);

  if (!result.valid) {
    return (
      <div style={{ padding: 20, backgroundColor: 'red', color: 'white' }}>
        <h2>Contract Enforcement Failed: {templateId}</h2>
        <ul>
          {result.errors.map((e, i) => (
            <li key={i}>
              <strong>{e.failureType}</strong>: {e.propName} (Expected: {e.expected}, Got: {e.received}) - {e.possibleResolution}
            </li>
          ))}
        </ul>
      </div>
    );
  }

  const Component = registry[templateId];
  if (!Component) {
    return (
      <div style={{ padding: 20, backgroundColor: 'red', color: 'white' }}>
        <h2>Component not found in registry: {templateId}</h2>
      </div>
    );
  }

  return <Component {...result.safeProps} />;
};
