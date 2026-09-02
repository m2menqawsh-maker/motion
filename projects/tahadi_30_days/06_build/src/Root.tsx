import React from "react";
import { Composition } from "remotion";
import { MainComposition } from "./compositions/generated/Root";

import "./rtl.css";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition 
        id="Main" 
        component={MainComposition} 
        durationInFrames={1560} 
        fps={30} 
        width={1080} 
        height={1920} 
      />
    </>
  );
};
