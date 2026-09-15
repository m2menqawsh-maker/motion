import React from "react";
import { AudiogramScene } from "../../remotion-app/src/remotion/scenes/audiogram-scene";
import type { TemplateProps } from "../../../registry/types";

export const AudiogramSceneWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <AudiogramScene  {...template_props} title={content?.text || undefined} subtitle={content?.lines?.[0] || undefined} />
  </div>
  );
};
