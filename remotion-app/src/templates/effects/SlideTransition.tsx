import React from "react";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { slide } from "@remotion/transitions/slide";

export const SlideTransition = ({ surface }: any) => {
  const direction = surface?.animation?.direction || "from-left";
  return (
    <TransitionSeries>
      <TransitionSeries.Sequence durationInFrames={30}>
        <div style={{ backgroundColor: surface?.background || "#000", width: "100%", height: "100%" }} />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition
        presentation={slide({ direction })}
        timing={linearTiming({ durationInFrames: 30 })}
      />
      <TransitionSeries.Sequence durationInFrames={30}>
        <div style={{ backgroundColor: surface?.color || "#fff", width: "100%", height: "100%" }} />
      </TransitionSeries.Sequence>
    </TransitionSeries>
  );
};
