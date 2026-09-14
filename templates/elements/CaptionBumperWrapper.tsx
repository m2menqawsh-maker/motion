import React from "react";
import { CaptionBumper } from "../../remotion-app/src/remotion/scenes/caption-bumper";
import type { TemplateProps } from "../../../registry/types";

export const CaptionBumperWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <CaptionBumper text={content?.text || undefined} />
  );
};
