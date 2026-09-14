import React from "react";
import { CaptionScene } from "../../remotion-app/src/remotion/scenes/caption-scene";
import type { TemplateProps } from "../../../registry/types";

export const CaptionSceneWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <CaptionScene label={content?.text || undefined} />
  );
};
