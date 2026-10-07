import React from "react";
import { Composition } from "remotion";
import { BlueprintVideo } from "./BlueprintVideo";
import { mergeProject, MergedProject, ProjectData } from "./merge";
import { TEMPLATE_REGISTRY } from "../../registry/template-registry";
import { BrandKit } from "../../contracts/brand";
import { TemplateGallery } from "./TemplateGallery";
import { Showcase, getShowcaseDuration } from "./Showcase";

export interface BlueprintVideoInputProps {
  projectData: ProjectData;
}

export interface CalculatedProps {
  projectData: MergedProject;
  brand: BrandKit;
}

// Dummy project data for studio preview if no inputProps are passed
const DUMMY_PROJECT_DATA: ProjectData = {
  project: { title: "Preview" },
  blueprint: { fps: 30, aspect_ratio: "16:9", scenes: [] },
  brand: {
    brandName: "Studio",
    logoSrc: null,
    colors: { primary: "#00F5FF", accent: "#FFD700", background: "#1a2238", text: "#FFFFFF" },
    fonts: { display: "Cairo", body: "Cairo" }
  }
};

import { parseRenderInput } from "../../contracts/render-input";
import { CanonicalVideo } from "./CanonicalVideo";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="CanonicalVideo"
        component={CanonicalVideo as React.FC<any>}
        width={1920}
        height={1080}
        defaultProps={{
          document: DUMMY_PROJECT_DATA.blueprint as any,
          brand: DUMMY_PROJECT_DATA.brand,
        }}
        calculateMetadata={async ({ props }) => {
          const doc = (props as any)?.document || (props as any)?.blueprint || props;
          const fps = doc?.fps || 30;
          let width = 1920;
          let height = 1080;
          const ratio = doc?.aspect_ratio;
          if (ratio === "9:16") {
            width = 1080;
            height = 1920;
          } else if (ratio === "1:1") {
            width = 1080;
            height = 1080;
          } else if (ratio === "4:5") {
            width = 1080;
            height = 1350;
          }
          let durationInFrames = doc?.totalDurationFrames;
          if (!durationInFrames && Array.isArray(doc?.scenes)) {
            durationInFrames = doc.scenes.reduce((acc: number, s: any) => {
              const end = (s.startFrame ?? 0) + (s.durationFrames ?? 1);
              return Math.max(acc, end);
            }, 0);
          }
          if (!durationInFrames || durationInFrames <= 0) {
            durationInFrames = 30;
          }
          return {
            fps,
            durationInFrames,
            width,
            height,
            props: {
              document: doc,
              brand: (props as any)?.brand || DUMMY_PROJECT_DATA.brand,
            },
          };
        }}
      />
      <Composition
        id="BlueprintVideo"
        component={BlueprintVideo as React.FC<any>}
        width={1080}
        height={1920}
        defaultProps={{
          projectData: DUMMY_PROJECT_DATA as any,
          brand: DUMMY_PROJECT_DATA.brand
        }}
        calculateMetadata={async ({ props }) => {
          // Canonical parse gate: validates raw input fail-closed before merge and mount (S16 - LED-044)
          const validated = parseRenderInput(props);
          
          // Merge defaults, overrides, brand tokens
          const projectData = mergeProject(validated, (template) => TEMPLATE_REGISTRY[template]);
          
          // Determine dimensions from aspect ratio
          let width = 1080;
          let height = 1920;
          const ratio = validated.blueprint?.aspect_ratio;
          if (ratio === "16:9") {
            width = 1920;
            height = 1080;
          } else if (ratio === "1:1") {
            width = 1080;
            height = 1080;
          }
          
          return {
            fps: projectData.fps || 30,
            durationInFrames: projectData.totalDurationFrames > 0 ? projectData.totalDurationFrames : 30,
            width,
            height,
            props: {
              projectData,
              brand: validated.brand
            }
          };
        }}
      />
      <Composition
        id="TemplateGallery"
        component={TemplateGallery}
        width={1920}
        height={1080}
        fps={30}
        durationInFrames={300}
      />
      <Composition
        id="Showcase"
        component={Showcase}
        width={1080}
        height={1920}
        fps={30}
        durationInFrames={getShowcaseDuration()}
      />
    </>
  );
};
