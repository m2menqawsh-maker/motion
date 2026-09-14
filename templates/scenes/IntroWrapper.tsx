import React from "react";
import { Intro } from "../../remotion-app/src/compositions/intro";
import type { TemplateProps } from "../../../registry/types";

export const IntroWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <Intro title={content?.text || undefined} subtitle={content?.lines?.[0] || undefined} />
  );
};
