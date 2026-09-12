import React from "react";
import { AbsoluteFill, Sequence } from "remotion";
import { IntroSection } from "./sections/IntroSection";
import { ScenesSection } from "./sections/ScenesSection";
import { ElementsSection } from "./sections/ElementsSection";
import { EffectsSection } from "./sections/EffectsSection";
import { EngineSection } from "./sections/EngineSection";
import { TransitionsSection } from "./sections/TransitionsSection";
import { TypographySection } from "./sections/TypographySection";
import { AssetsSection } from "./sections/AssetsSection";
import { MasterCombinationSection } from "./sections/MasterCombinationSection";

// Section Durations (in frames at 30 fps)
export const SECTION_TIMINGS = {
  intro: { from: 0, duration: 150 },                 // 5s
  scenes: { from: 150, duration: 300 },              // 10s
  elements: { from: 450, duration: 300 },            // 10s
  effects: { from: 750, duration: 240 },             // 8s
  engine: { from: 990, duration: 240 },              // 8s
  transitions: { from: 1230, duration: 240 },        // 8s
  typography: { from: 1470, duration: 240 },         // 8s
  assets: { from: 1710, duration: 180 },             // 6s
  master: { from: 1890, duration: 210 },             // 7s
};

export const SYSTEM_SHOWCASE_TOTAL_FRAMES = 2100; // 70 seconds total

export const SystemShowcase: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: "#060813" }}>
      <Sequence from={SECTION_TIMINGS.intro.from} durationInFrames={SECTION_TIMINGS.intro.duration}>
        <IntroSection />
      </Sequence>

      <Sequence from={SECTION_TIMINGS.scenes.from} durationInFrames={SECTION_TIMINGS.scenes.duration}>
        <ScenesSection />
      </Sequence>

      <Sequence from={SECTION_TIMINGS.elements.from} durationInFrames={SECTION_TIMINGS.elements.duration}>
        <ElementsSection />
      </Sequence>

      <Sequence from={SECTION_TIMINGS.effects.from} durationInFrames={SECTION_TIMINGS.effects.duration}>
        <EffectsSection />
      </Sequence>

      <Sequence from={SECTION_TIMINGS.engine.from} durationInFrames={SECTION_TIMINGS.engine.duration}>
        <EngineSection />
      </Sequence>

      <Sequence from={SECTION_TIMINGS.transitions.from} durationInFrames={SECTION_TIMINGS.transitions.duration}>
        <TransitionsSection />
      </Sequence>

      <Sequence from={SECTION_TIMINGS.typography.from} durationInFrames={SECTION_TIMINGS.typography.duration}>
        <TypographySection />
      </Sequence>

      <Sequence from={SECTION_TIMINGS.assets.from} durationInFrames={SECTION_TIMINGS.assets.duration}>
        <AssetsSection />
      </Sequence>

      <Sequence from={SECTION_TIMINGS.master.from} durationInFrames={SECTION_TIMINGS.master.duration}>
        <MasterCombinationSection />
      </Sequence>
    </AbsoluteFill>
  );
};
