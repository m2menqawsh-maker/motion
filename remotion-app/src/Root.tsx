import React from "react";
import { Composition } from "remotion";
import { BlueprintVideo } from "./BlueprintVideo";
import { mergeProject, MergedProject, ProjectData } from "./merge";
import { TEMPLATE_REGISTRY } from "../../registry/template-registry";
import { BrandKit } from "../../contracts/brand";

export interface BlueprintVideoInputProps {
  projectData: ProjectData;
}

export interface CalculatedProps {
  projectData: MergedProject;
  brand: BrandKit;
}

// Dummy project data for studio preview if no inputProps are passed
const DUMMY_PROJECT_DATA: ProjectData = {
  project: { fps: 30, title: "Preview" },
  blueprint: { scenes: [] },
  brand: {
    brandName: "Studio",
    logoSrc: null,
    colors: { primary: "#00F5FF", accent: "#FFD700", background: "#0A0E27", text: "#FFFFFF" },
    fonts: { display: "Cairo", body: "Cairo" }
  }
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="BlueprintVideo"
      component={BlueprintVideo}
      width={1080}
      height={1920}
      defaultProps={{
        projectData: DUMMY_PROJECT_DATA
      } as BlueprintVideoInputProps}
      calculateMetadata={async ({ props }) => {
        const { projectData: rawData } = props as BlueprintVideoInputProps;
        
        // Merge defaults, overrides, brand tokens
        const projectData = mergeProject(rawData, (template) => TEMPLATE_REGISTRY[template]);
        
        return {
          fps: projectData.fps,
          durationInFrames: projectData.totalDurationFrames > 0 ? projectData.totalDurationFrames : 30,
          props: {
            projectData,
            brand: rawData.brand
          }
        };
      }}
    />
  );
};
