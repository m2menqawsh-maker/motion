import React from "react";
import { AutoFitTitle } from "../../remotion-app/src/remotion/scenes/auto-fit-title";
import type { TemplateProps } from "../../../registry/types";

export const AutoFitTitleWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <AutoFitTitle title={content?.text || undefined} subtitle={content?.lines?.[0] || undefined} />
  );
};
