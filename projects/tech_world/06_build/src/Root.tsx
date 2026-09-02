import { Scene1 } from './compositions/Scene1';
import { Scene2 } from './compositions/Scene2';
import { MainComposition } from './compositions/MainComposition';
import React from "react";
import { Composition, staticFile } from "remotion";
import { SurgicalSutureAd, SURGICAL_AD_DURATION_FRAMES } from "./SurgicalSutureAd";
import { SocialClip } from "./premium-templates/scenes/social-clip/index";
import { Intro } from "@/compositions/intro/index";
import { Showcase } from "@/compositions/showcase/index";
import { HeroLoop } from "@/compositions/hero-loop/index";
import { DataStory } from "@/compositions/data-story/index";
import { CreatorReel } from "@/compositions/creator-reel/index";
import { PodcastClip } from "@/compositions/podcast-clip/index";
import { HeroDeviceAssemble } from "@/compositions/hero-device-assemble/index";
import { EcosystemOrbit } from "@/compositions/ecosystem-orbit/index";
import { BentoPan } from "@/compositions/bento-pan/index";
import { BrowserFlow } from "@/compositions/browser-flow/index";
import { AiGenerationCanvas } from "@/compositions/ai-generation-canvas/index";
import { AiComposerShowcase } from "@/compositions/ai-composer-showcase/index";
import { LiveCodeSplit } from "@/compositions/live-code-split/index";
import { DeployReveal } from "@/compositions/deploy-reveal/index";
import { DashboardPopulate } from "@/compositions/dashboard-populate/index";
import { PricingFocus } from "@/compositions/pricing-focus/index";
import { LandingCodeShowcase } from "@/compositions/landing-code-showcase/index";
import { ToolMenuSlide } from "@/compositions/tool-menu-slide/index";
import { ImageExpand } from "@/compositions/image-expand/index";
import { SystemShowcase, SYSTEM_SHOWCASE_TOTAL_FRAMES } from "@/compositions/system-showcase/SystemShowcase";

export const RemotionRoot: React.FC = () => {
  console.log('Scene1:', Scene1, 'Scene2:', Scene2, 'MainComposition:', MainComposition);
  return (
    <>
      <Composition id="MainComposition" component={MainComposition} durationInFrames={1020} fps={30} width={1080} height={1920} />
      <Composition id="Scene1" component={Scene1} durationInFrames={176} fps={30} width={1080} height={1920} />
      <Composition id="Scene2" component={Scene2} durationInFrames={419} fps={30} width={1080} height={1920} />
      <Composition
        id="SocialClip"
        component={SocialClip}
        durationInFrames={228}
        fps={30}
        width={1080}
        height={1920}
      />
          <Composition
        id="Intro"
        component={Intro}
        durationInFrames={150}
        fps={30}
        width={1920}
        height={1080}
      />
          <Composition
        id="Showcase"
        component={Showcase}
        durationInFrames={240}
        fps={30}
        width={1920}
        height={1080}
      />
          <Composition
        id="HeroLoop"
        component={HeroLoop}
        durationInFrames={360}
        fps={30}
        width={1920}
        height={1080}
      />
          <Composition
        id="DataStory"
        component={DataStory}
        defaultProps={{
          title: "Pipeline Metrics",
          subtitle: "Real-time rendering performance",
          barData: [
            { label: "Q1", value: 40 },
            { label: "Q2", value: 65 },
            { label: "Q3", value: 85 },
            { label: "Q4", value: 95 },
          ],
          metrics: [
            { label: "Throughput", value: 120, suffix: "%" },
            { label: "Latency", value: 636, suffix: "ms" },
            { label: "Templates", value: 172 },
          ],
          steps: [
            { title: "Discovery", description: "Scan templates and indexes" },
            { title: "Composition", description: "Assemble dynamic timeline" },
            { title: "Studio", description: "Live instant preview" },
          ],
        }}
        durationInFrames={420}
        fps={30}
        width={1920}
        height={1080}
      />
          <Composition
        id="CreatorReel"
        component={CreatorReel}
        durationInFrames={390}
        fps={30}
        width={1080}
        height={1920}
      />
          <Composition
        id="PodcastClip"
        component={PodcastClip}
        defaultProps={{
          audioSrc: staticFile("media/audio/digital_norm.wav"),
          captions: [
            { text: "Welcome", startMs: 0, endMs: 800, timestampMs: 0, confidence: 1 },
            { text: "to", startMs: 800, endMs: 1200, timestampMs: 800, confidence: 1 },
            { text: "the", startMs: 1200, endMs: 1600, timestampMs: 1200, confidence: 1 },
            { text: "Showcase", startMs: 1600, endMs: 2500, timestampMs: 1600, confidence: 1 },
          ],
          title: "Clean Audio Architecture",
          subtitle: "Commercial Motion Pipeline",
          showName: "Antigravity Studio",
        }}
        durationInFrames={294}
        fps={30}
        width={1080}
        height={1920}
      />
          <Composition
        id="HeroDeviceAssemble"
        component={HeroDeviceAssemble}
        durationInFrames={180}
        fps={30}
        width={1920}
        height={1080}
      />
          <Composition
        id="EcosystemOrbit"
        component={EcosystemOrbit}
        durationInFrames={180}
        fps={30}
        width={1920}
        height={1080}
      />
          <Composition
        id="BentoPan"
        component={BentoPan}
        durationInFrames={180}
        fps={30}
        width={1920}
        height={1080}
      />
          <Composition
        id="BrowserFlow"
        component={BrowserFlow}
        durationInFrames={168}
        fps={30}
        width={1920}
        height={1080}
      />
          <Composition
        id="AiGenerationCanvas"
        component={AiGenerationCanvas}
        durationInFrames={180}
        fps={30}
        width={1920}
        height={1080}
      />
          <Composition
        id="AiComposerShowcase"
        component={AiComposerShowcase}
        durationInFrames={533}
        fps={30}
        width={1920}
        height={1080}
      />
          <Composition
        id="LiveCodeSplit"
        component={LiveCodeSplit}
        durationInFrames={168}
        fps={30}
        width={1920}
        height={1080}
      />
          <Composition
        id="DeployReveal"
        component={DeployReveal}
        durationInFrames={168}
        fps={30}
        width={1920}
        height={1080}
      />
          <Composition
        id="DashboardPopulate"
        component={DashboardPopulate}
        durationInFrames={168}
        fps={30}
        width={1920}
        height={1080}
      />
          <Composition
        id="PricingFocus"
        component={PricingFocus}
        durationInFrames={180}
        fps={30}
        width={1920}
        height={1080}
      />
          <Composition
        id="LandingCodeShowcase"
        component={LandingCodeShowcase}
        durationInFrames={180}
        fps={30}
        width={1920}
        height={1080}
      />
          <Composition
        id="ToolMenuSlide"
        component={ToolMenuSlide}
        durationInFrames={120}
        fps={30}
        width={1920}
        height={1080}
      />
          <Composition
        id="ImageExpand"
        component={ImageExpand}
        durationInFrames={120}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};




