import React from "react";
import { MediaFrame } from "../../remotion-app/src/remotion/scenes/media-frame";
import type { TemplateProps } from "../../../registry/types";

export const MediaFrameWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <MediaFrame title={content?.text || undefined} />
  );
};
