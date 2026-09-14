import React from "react";
import { LandingCodeShowcase } from "../../remotion-app/src/compositions/landing-code-showcase";
import type { TemplateProps } from "../../../registry/types";

export const LandingCodeShowcaseWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <LandingCodeShowcase  />
  );
};
