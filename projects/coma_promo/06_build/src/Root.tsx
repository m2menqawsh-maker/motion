import React from "react";
import { Composition } from "remotion";
import { ComaPromo } from "./ComaPromo";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="ComaPromo"
        component={ComaPromo}
        durationInFrames={515}
        fps={30}
        width={1080}
        height={1920}
      />
    </>
  );
};
