import * as fs from 'fs';
import * as path from 'path';
import { BuildResult } from './types';

export function generateCompositionRoot(result: BuildResult): string {
  const scenes = result.plan.scenes;
  const imports: string[] = [];
  const sequenceElements: string[] = [];

  scenes.forEach((scene, index) => {
    const varName = `Template_${index}`;
    imports.push(`import { ${scene.componentExportName} as ${varName} } from '${scene.componentImportPath}';`);
    
    // We use standard Sequence placement. Transitions can be added later as an optional path.
    sequenceElements.push(`
      <Sequence from={${scene.spec.startFrame}} durationInFrames={${scene.spec.durationInFrames}}>
        <${varName} {...(${JSON.stringify(scene.normalizedProps)})} />
      </Sequence>
    `);
  });

  const rootCode = `
import React from 'react';
import { Composition, Sequence } from 'remotion';
${imports.join('\n')}

export const OrchestratedVideo: React.FC = () => {
  return (
    <>
      ${sequenceElements.join('\n')}
    </>
  );
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="OrchestratedVideo"
      component={OrchestratedVideo}
      durationInFrames={${result.plan.duration}}
      fps={${result.plan.fps}}
      width={${result.plan.resolution.width}}
      height={${result.plan.resolution.height}}
    />
  );
};

import { registerRoot } from 'remotion';
registerRoot(RemotionRoot);
  `.trim();

  const outPath = path.join(__dirname, 'OrchestratedRoot.tsx');
  fs.writeFileSync(outPath, rootCode, 'utf-8');
  return outPath;
}
