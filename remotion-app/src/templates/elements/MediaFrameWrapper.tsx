import React from "react";
import { MediaFrame } from "../../remotion-app/src/remotion/scenes/media-frame";
import type { TemplateProps } from "../../../registry/types";

export const MediaFrameWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <MediaFrame  {...template_props} title={content?.text || undefined} />
  </div>
  );
};
