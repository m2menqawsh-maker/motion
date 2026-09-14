import React from "react";
import { DeployReveal } from "../../remotion-app/src/compositions/deploy-reveal";
import type { TemplateProps } from "../../../registry/types";

export const DeployRevealWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <DeployReveal  />
  );
};
