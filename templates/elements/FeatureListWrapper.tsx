import React from "react";
import { FeatureList } from "../../remotion-app/src/remotion/scenes/feature-list";
import type { TemplateProps } from "../../../registry/types";

export const FeatureListWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <FeatureList title={content?.text || undefined} />
  );
};
