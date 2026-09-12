
import React from 'react';
import { Composition, registerRoot } from 'remotion';
import { TemplateAdapter } from '../contract/TemplateAdapter';
import Comp from '../../templates/effects/overlays/vignette-pulse';

const registry: Record<string, React.FC<any>> = {
  "effects/overlays/vignette-pulse": Comp as any
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="CertificationHarness"
      component={TemplateAdapter}
      durationInFrames={30}
      fps={30}
      width={1080}
      height={1080}
      defaultProps={{
        templateId: "effects/overlays/vignette-pulse",
        props: {"_status":"GENERATED"},
        registry
      }}
    />
  );
};

registerRoot(RemotionRoot);
