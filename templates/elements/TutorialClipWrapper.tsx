import React from "react";
import { TutorialClip } from "../../remotion-app/src/compositions/tutorial-clip";
import type { TemplateProps } from "../../../registry/types";

export const TutorialClipWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <TutorialClip title={content?.text || undefined} subtitle={content?.lines?.[0] || undefined} />
  );
};
