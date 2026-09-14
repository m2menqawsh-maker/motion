import React from "react";
import { Composition } from "remotion";
import { BlueprintVideo } from "./BlueprintVideo";
import { mergeProject, MergedProject, ProjectData } from "./merge";
import { TEMPLATE_REGISTRY } from "../../registry/template-registry";
import { BrandKit } from "../../contracts/brand";
import { TemplateGallery } from "./TemplateGallery";

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
          console.log("=== DEBUG RAW DATA ===", JSON.stringify(rawData));
          
          // Merge defaults, overrides, brand tokens
          const projectData = mergeProject(rawData, (template) => TEMPLATE_REGISTRY[template]);
          console.log("=== DEBUG MERGED DATA ===", projectData.totalDurationFrames, projectData.scenes.length);
          
          return {
            fps: projectData.fps || 30,
            durationInFrames: projectData.totalDurationFrames > 0 ? projectData.totalDurationFrames : 30,
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
    </>
  );
};
