import React from "react";
import { SplitScreen } from "../../remotion-app/src/remotion/scenes/split-screen";
import type { TemplateProps } from "../../../registry/types";

export const SplitScreenWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <SplitScreen title={content?.text || undefined} />
  );
};
