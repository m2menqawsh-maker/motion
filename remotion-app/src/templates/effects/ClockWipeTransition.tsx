import React from "react";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { clockWipe } from "@remotion/transitions/clock-wipe";

export const ClockWipeTransition = ({ surface }: any) => {
  const width = surface?.width || 1080;
  const height = surface?.height || 1920;
  
  return (
    <TransitionSeries>
      <TransitionSeries.Sequence durationInFrames={30}>
        <div style={{ backgroundColor: surface?.background || "#000", width: "100%", height: "100%" }} />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition
        presentation={clockWipe({ width, height })}
        timing={linearTiming({ durationInFrames: 30 })}
      />
      <TransitionSeries.Sequence durationInFrames={30}>
        <div style={{ backgroundColor: surface?.color || "#fff", width: "100%", height: "100%" }} />
      </TransitionSeries.Sequence>
    </TransitionSeries>
  );
};
