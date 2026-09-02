import React from "react";
import { Composition } from "remotion";
import { Scene1 } from './compositions/Scene1';
import { Scene2 } from './compositions/Scene2';
import { Scene3 } from './compositions/Scene3';
import { Scene4 } from './compositions/Scene4';
import { Scene5 } from './compositions/Scene5';
import { MainComposition } from './compositions/MainComposition';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition id="MainComposition" component={MainComposition} durationInFrames={535} fps={30} width={1080} height={1920} />
      <Composition id="Scene1" component={Scene1} durationInFrames={148} fps={30} width={1080} height={1920} />
      <Composition id="Scene2" component={Scene2} durationInFrames={88} fps={30} width={1080} height={1920} />
      <Composition id="Scene3" component={Scene3} durationInFrames={165} fps={30} width={1080} height={1920} />
      <Composition id="Scene4" component={Scene4} durationInFrames={44} fps={30} width={1080} height={1920} />
      <Composition id="Scene5" component={Scene5} durationInFrames={90} fps={30} width={1080} height={1920} />
    </>
  );
};
