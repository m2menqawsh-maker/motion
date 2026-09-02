import React from "react";
import { Composition, Sequence, Audio, staticFile } from "remotion";
import { Scene1Hook, SCENE_1_DURATION_FRAMES } from "./Scene1Hook";
import { Scene2Promise, SCENE_2_DURATION_FRAMES } from "./Scene2Promise";
import { Scene3Foundations, SCENE_3_DURATION_FRAMES } from "./Scene3Foundations";
import { Scene4OOP, SCENE_4_DURATION_FRAMES } from "./Scene4OOP";
import { Scene5Projects, SCENE_5_DURATION_FRAMES } from "./Scene5Projects";
import { Scene6Showcase, SCENE_6_DURATION_FRAMES } from "./Scene6Showcase";
import { Scene7Twist, SCENE_7_DURATION_FRAMES } from "./Scene7Twist";
import { Scene8Golden, SCENE_8_DURATION_FRAMES } from "./Scene8Golden";
import { Scene9CTA, SCENE_9_DURATION_FRAMES } from "./Scene9CTA";
import { UnifiedCyberBackground } from "./UnifiedCyberBackground";

export const TOTAL_SCENES_1_AND_2 =
  SCENE_1_DURATION_FRAMES + SCENE_2_DURATION_FRAMES; // 86 + 137 = 223 frames (7.44s)

export const TOTAL_SCENES_1_TO_3 =
  TOTAL_SCENES_1_AND_2 + SCENE_3_DURATION_FRAMES; // 465 frames (15.50s)

export const TOTAL_SCENES_1_TO_4 =
  TOTAL_SCENES_1_TO_3 + SCENE_4_DURATION_FRAMES; // 716 frames (23.88s)

export const TOTAL_SCENES_1_TO_5 =
  TOTAL_SCENES_1_TO_4 + SCENE_5_DURATION_FRAMES; // 849 frames (28.3s)

export const TOTAL_SCENES_1_TO_6 =
  TOTAL_SCENES_1_TO_5 + SCENE_6_DURATION_FRAMES; // 998 frames (33.26s)

export const TOTAL_SCENES_1_TO_7 =
  TOTAL_SCENES_1_TO_6 + SCENE_7_DURATION_FRAMES; // 1270 frames (with silences)

export const TOTAL_SCENES_1_TO_8 =
  TOTAL_SCENES_1_TO_7 + SCENE_8_DURATION_FRAMES; // 1398 frames

export const TOTAL_SCENES_1_TO_9 =
  TOTAL_SCENES_1_TO_8 + SCENE_9_DURATION_FRAMES; // 1653 frames (55.1s)

/**
 * Linked Continuous Timeline: Scene 1 to Scene 9
 * Features a single, continuous Unified Cyber Background that never cuts or resets!
 */
export const MainComposition: React.FC = () => {
  return (
    <>
      {/* Global Modern Tech Google Fonts: Alexandria + IBM Plex Sans Arabic + JetBrains Mono */}
      <style>
        {`
          @import url('https://fonts.googleapis.com/css2?family=Alexandria:wght@600;700;800;900;950&family=IBM+Plex+Sans+Arabic:wght@600;700;800&family=JetBrains+Mono:wght@700;800&display=swap');
          * {
            font-family: 'Alexandria', 'IBM Plex Sans Arabic', -apple-system, BlinkMacSystemFont, sans-serif;
          }
        `}
      </style>

      {/* 1. Global Continuous Unified Cyber Background */}
      <UnifiedCyberBackground />

      {/* 2. Master Audio Track */}
      {/* BGM plays continuously, but boosts volume during silent gaps */}
      <Audio 
        src={staticFile("media/bg_music.wav")} 
        volume={(f) => {
          // Gap 1: Scene 6 -> 7 (998 to 1013)
          if (f >= 990 && f <= 1020) return 0.5;
          // Gap 2: End of Scene 7 (1180 to 1240)
          if (f >= 1180 && f <= 1240) return 0.5;
          // Gap 3: Scene 8 -> 9 (1368 to 1404)
          if (f >= 1358 && f <= 1404) return 0.5;
          return 0.16;
        }} 
      />

      {/* VO Part 1: Scenes 1 to 6 */}
      <Sequence from={0} durationInFrames={TOTAL_SCENES_1_TO_6}>
        <Audio src={staticFile("media/vo_audio.wav")} startFrom={0} endAt={TOTAL_SCENES_1_TO_6} volume={1.0} />
      </Sequence>

      {/* VO Part 2: Scene 7 Core VO. 
          Delayed by 15 frames of pure black silence at the start of Scene 7.
          It stops at 1180 (the end of "ما بتكفي").
          After it stops, there are 15 frames of extra tension silence. */}
      <Sequence from={TOTAL_SCENES_1_TO_6 + 15} durationInFrames={182}>
        <Audio src={staticFile("media/vo_audio.wav")} startFrom={TOTAL_SCENES_1_TO_6} endAt={TOTAL_SCENES_1_TO_6 + 182} volume={1.0} />
      </Sequence>

      {/* VO Part 3: Future Scenes (Starts at 1180 + 15 + 15 offset = 1210) */}
      <Sequence from={TOTAL_SCENES_1_TO_7}>
        <Audio src={staticFile("media/vo_audio.wav")} startFrom={TOTAL_SCENES_1_TO_6 + 182} volume={1.0} />
      </Sequence>

      {/* Scene 1: The Hook (0 - 86 frames / 0.0s - 2.88s) */}
      <Sequence from={0} durationInFrames={SCENE_1_DURATION_FRAMES} name="Scene 1: The Hook">
        <Scene1Hook includeGlobalAudio={false} />
      </Sequence>

      {/* Scene 2: The Big Promise (86 - 223 frames / 2.88s - 7.44s) */}
      <Sequence
        from={SCENE_1_DURATION_FRAMES}
        durationInFrames={SCENE_2_DURATION_FRAMES}
        name="Scene 2: The Promise"
      >
        <Scene2Promise includeGlobalAudio={false} />
      </Sequence>

      {/* Scene 3: Days 1-10 Foundations (223 - 465 frames / 7.44s - 15.50s) */}
      <Sequence
        from={TOTAL_SCENES_1_AND_2}
        durationInFrames={SCENE_3_DURATION_FRAMES}
        name="Scene 3: Days 1-10"
      >
        <Scene3Foundations includeGlobalAudio={false} />
      </Sequence>

      {/* Scene 4: Days 11-20 Deep OOP & Clean Architecture (465 - 716 frames / 15.50s - 23.88s) */}
      <Sequence
        from={TOTAL_SCENES_1_TO_3}
        durationInFrames={SCENE_4_DURATION_FRAMES}
        name="Scene 4: Days 11-20 OOP"
      >
        <Scene4OOP includeGlobalAudio={false} />
      </Sequence>

      {/* Scene 5: Days 21-30 Projects (716 - 849 frames / 23.88s - 28.3s) */}
      <Sequence
        from={TOTAL_SCENES_1_TO_4}
        durationInFrames={SCENE_5_DURATION_FRAMES}
        name="Scene 5: Days 21-30 Projects"
      >
        <Scene5Projects includeGlobalAudio={false} />
      </Sequence>

      {/* Scene 6: Projects Showcase (849 - 998 frames / 28.3s - 33.26s) */}
      <Sequence
        from={TOTAL_SCENES_1_TO_5}
        durationInFrames={SCENE_6_DURATION_FRAMES}
        name="Scene 6: Projects Showcase"
      >
        <Scene6Showcase includeGlobalAudio={false} />
      </Sequence>

      {/* Scene 7: The Twist (998 - 1270 frames / 33.26s - 39.32s + extra silences) */}
      <Sequence
        from={TOTAL_SCENES_1_TO_6}
        durationInFrames={SCENE_7_DURATION_FRAMES}
        name="Scene 7: The Twist"
      >
        <Scene7Twist includeGlobalAudio={false} />
      </Sequence>

      {/* Scene 8: The Golden Equation (1270 - 1398 frames / 39.32s - 43.58s) */}
      <Sequence
        from={TOTAL_SCENES_1_TO_7}
        durationInFrames={SCENE_8_DURATION_FRAMES}
        name="Scene 8: The Golden Equation"
      >
        <Scene8Golden includeGlobalAudio={false} />
      </Sequence>

      {/* Scene 9: Call To Action (1398 - 1653 frames / 43.58s - 52.08s) */}
      <Sequence
        from={TOTAL_SCENES_1_TO_8}
        durationInFrames={SCENE_9_DURATION_FRAMES}
        name="Scene 9: Call To Action"
      >
        <Scene9CTA includeGlobalAudio={false} />
      </Sequence>
    </>
  );
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* Primary Composition: Scenes 1 -> 9 Linked Master Timeline (1653 frames) */}
      <Composition
        id="MainComposition"
        component={MainComposition}
        durationInFrames={TOTAL_SCENES_1_TO_9}
        fps={30}
        width={1080}
        height={1920}
      />

      {/* Standalone Scene 9 */}
      <Composition
        id="PythonChallengeScene9"
        component={() => <Scene9CTA includeGlobalAudio={true} />}
        durationInFrames={SCENE_9_DURATION_FRAMES}
        fps={30}
        width={1080}
        height={1920}
      />

      {/* Standalone Scene 8 */}
      <Composition
        id="PythonChallengeScene8"
        component={() => <Scene8Golden includeGlobalAudio={true} />}
        durationInFrames={SCENE_8_DURATION_FRAMES}
        fps={30}
        width={1080}
        height={1920}
      />

      {/* Standalone Scene 7 */}
      <Composition
        id="PythonChallengeScene7"
        component={() => <Scene7Twist includeGlobalAudio={true} />}
        durationInFrames={SCENE_7_DURATION_FRAMES}
        fps={30}
        width={1080}
        height={1920}
      />

      {/* Standalone Scene 6 */}
      <Composition
        id="PythonChallengeScene6"
        component={() => <Scene6Showcase includeGlobalAudio={true} />}
        durationInFrames={SCENE_6_DURATION_FRAMES}
        fps={30}
        width={1080}
        height={1920}
      />

      {/* Standalone Scene 5 */}
      <Composition
        id="PythonChallengeScene5"
        component={() => <Scene5Projects includeGlobalAudio={true} />}
        durationInFrames={SCENE_5_DURATION_FRAMES}
        fps={30}
        width={1080}
        height={1920}
      />

      {/* Standalone Scene 4 */}
      <Composition
        id="PythonChallengeScene4"
        component={() => <Scene4OOP includeGlobalAudio={true} />}
        durationInFrames={SCENE_4_DURATION_FRAMES}
        fps={30}
        width={1080}
        height={1920}
      />

      {/* Standalone Scene 3 */}
      <Composition
        id="PythonChallengeScene3"
        component={() => <Scene3Foundations includeGlobalAudio={true} />}
        durationInFrames={SCENE_3_DURATION_FRAMES}
        fps={30}
        width={1080}
        height={1920}
      />

      {/* Standalone Scene 2 */}
      <Composition
        id="PythonChallengeScene2"
        component={() => <Scene2Promise includeGlobalAudio={true} />}
        durationInFrames={SCENE_2_DURATION_FRAMES}
        fps={30}
        width={1080}
        height={1920}
      />

      {/* Standalone Scene 1 */}
      <Composition
        id="PythonChallengeScene1"
        component={() => <Scene1Hook includeGlobalAudio={true} />}
        durationInFrames={SCENE_1_DURATION_FRAMES}
        fps={30}
        width={1080}
        height={1920}
      />
    </>
  );
};
