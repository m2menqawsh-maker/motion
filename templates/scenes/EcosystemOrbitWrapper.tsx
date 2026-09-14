import React from "react";
import { EcosystemOrbit } from "../../remotion-app/src/compositions/ecosystem-orbit";
import type { TemplateProps } from "../../../registry/types";

export const EcosystemOrbitWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <EcosystemOrbit  />
  );
};
