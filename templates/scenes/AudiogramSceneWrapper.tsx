import React from "react";
import { AudiogramScene } from "../../remotion-app/src/remotion/scenes/audiogram-scene";
import type { TemplateProps } from "../../../registry/types";

export const AudiogramSceneWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <AudiogramScene title={content?.text || undefined} subtitle={content?.lines?.[0] || undefined} />
  );
};
