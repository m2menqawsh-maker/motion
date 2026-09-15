import React from "react";
import { CaptionScene } from "../../remotion-app/src/remotion/scenes/caption-scene";
import type { TemplateProps } from "../../../registry/types";

export const CaptionSceneWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <CaptionScene  {...template_props} label={content?.text || undefined} />
  </div>
  );
};
