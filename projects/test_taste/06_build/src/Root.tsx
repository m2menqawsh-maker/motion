import React from "react";
import { Composition } from "remotion";
import { MainComposition } from "./compositions/generated/Root";
import { Scene1 } from "./compositions/generated/Scene1";
import { Scene2 } from "./compositions/generated/Scene2";
import { Scene3 } from "./compositions/generated/Scene3";

import "./rtl.css";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="Main"
        component={MainComposition}
        durationInFrames={296}
        fps={30}
        width={1080}
        height={1920}
      />
      <Composition id="Scene1" component={Scene1} durationInFrames={150} fps={30} width={1080} height={1920} />
      <Composition id="Scene2" component={Scene2} durationInFrames={150} fps={30} width={1080} height={1920} />
      <Composition id="Scene3" component={Scene3} durationInFrames={150} fps={30} width={1080} height={1920} />
    </>
  );
};
