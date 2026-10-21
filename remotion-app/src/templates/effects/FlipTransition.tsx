import React from "react";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { flip } from "@remotion/transitions/flip";

export const FlipTransition = ({ surface }: any) => {
  const direction = surface?.animation?.direction || "horizontal";
  
  return (
    <TransitionSeries>
      <TransitionSeries.Sequence durationInFrames={30}>
        <div style={{ backgroundColor: surface?.background || "#000", width: "100%", height: "100%" }} />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition
        presentation={flip({ direction })}
        timing={linearTiming({ durationInFrames: 30 })}
      />
      <TransitionSeries.Sequence durationInFrames={30}>
        <div style={{ backgroundColor: surface?.color || "#fff", width: "100%", height: "100%" }} />
      </TransitionSeries.Sequence>
    </TransitionSeries>
  );
};
