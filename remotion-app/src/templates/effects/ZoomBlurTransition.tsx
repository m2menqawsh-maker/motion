import React from "react";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { zoomBlur } from "@remotion/transitions/zoom-blur";

export const ZoomBlurTransition = ({ surface }: any) => {
  return (
    <TransitionSeries>
      <TransitionSeries.Sequence durationInFrames={30}>
        <div style={{ backgroundColor: surface?.background || "#000", width: "100%", height: "100%" }} />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition
        presentation={zoomBlur({} as any)}
        timing={linearTiming({ durationInFrames: 30 })}
      />
      <TransitionSeries.Sequence durationInFrames={30}>
        <div style={{ backgroundColor: surface?.color || "#fff", width: "100%", height: "100%" }} />
      </TransitionSeries.Sequence>
    </TransitionSeries>
  );
};
