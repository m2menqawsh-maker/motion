import React from "react";
import { LowerThird } from "../../remotion-app/src/remotion/scenes/lower-third";
import type { TemplateProps } from "../../../registry/types";

export const LowerThirdWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <LowerThird title={content?.text || undefined} subtitle={content?.lines?.[0] || undefined} />
  );
};
