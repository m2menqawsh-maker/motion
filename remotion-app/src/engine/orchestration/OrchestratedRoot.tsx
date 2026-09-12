import React from 'react';
import { Composition, Sequence } from 'remotion';
import { SocialClip as Template_0 } from '../../templates/scenes/social/SocialClip';
import { SocialClip as Template_1 } from '../../templates/scenes/social/social-clip/index';
import { BlurOutUp as Template_2 } from '../../templates/effects/transitions/blur-out-up';

export const OrchestratedVideo: React.FC = () => {
  return (
    <>
      
      <Sequence from={0} durationInFrames={120}>
        <Template_0 {...({"hookTitle":"Social Clip Default","captions":[{"text":"This","startMs":0,"endMs":1000,"timestampMs":0,"confidence":1},{"text":"is","startMs":1000,"endMs":2000,"timestampMs":1000,"confidence":1},{"text":"SocialClip","startMs":2000,"endMs":4000,"timestampMs":2000,"confidence":1}]})} />
      </Sequence>
    

      <Sequence from={120} durationInFrames={120}>
        <Template_1 {...({"hookTitle":"Social Clip Index","captions":[{"text":"And","startMs":0,"endMs":1000,"timestampMs":0,"confidence":1},{"text":"social-clip/index","startMs":1000,"endMs":4000,"timestampMs":1000,"confidence":1}]})} />
      </Sequence>
    

      <Sequence from={240} durationInFrames={120}>
        <Template_2 {...({"text":"Control Template","headline":"Control Template","body_text":"Testing generic execution hasn't regressed"})} />
      </Sequence>
    
    </>
  );
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="OrchestratedVideo"
      component={OrchestratedVideo}
      durationInFrames={360}
      fps={30}
      width={1080}
      height={1920}
    />
  );
};

import { registerRoot } from 'remotion';
registerRoot(RemotionRoot);