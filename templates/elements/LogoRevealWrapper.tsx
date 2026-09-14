import React from "react";
import { LogoReveal } from "../../remotion-app/src/remotion/scenes/logo-reveal";
import type { TemplateProps } from "../../../registry/types";

export const LogoRevealWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <LogoReveal  />
  );
};
