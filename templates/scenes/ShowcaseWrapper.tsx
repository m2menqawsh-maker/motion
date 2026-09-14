import React from "react";
import { Showcase } from "../../remotion-app/src/compositions/showcase";
import type { TemplateProps } from "../../../registry/types";

export const ShowcaseWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <Showcase title={content?.text || undefined} subtitle={content?.lines?.[0] || undefined} />
  );
};
