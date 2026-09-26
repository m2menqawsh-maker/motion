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
    colors: { primary: "#00F5FF", accent: "#FFD700", background: "#0A0E27", text: "#FFFFFF" },
    fonts: { display: "Cairo", body: "Cairo" }
  }
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
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
          const { projectData: rawData } = props as unknown as BlueprintVideoInputProps;
          
          // Merge defaults, overrides, brand tokens
          const projectData = mergeProject(rawData, (template) => TEMPLATE_REGISTRY[template]);
          
          // Determine dimensions from aspect ratio
          let width = 1080;
          let height = 1920;
          const ratio = rawData.blueprint?.aspect_ratio;
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
              brand: rawData.brand
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
