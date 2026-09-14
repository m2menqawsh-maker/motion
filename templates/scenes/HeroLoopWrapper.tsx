import React from "react";
import { HeroLoop } from "../../remotion-app/src/compositions/hero-loop";
import type { TemplateProps } from "../../../registry/types";

export const HeroLoopWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <HeroLoop  />
  );
};
