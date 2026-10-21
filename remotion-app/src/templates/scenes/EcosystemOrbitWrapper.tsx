import React from "react";
import { EcosystemOrbit } from "@/compositions/ecosystem-orbit";
import type { TemplateProps } from "@registry/types";

export const EcosystemOrbitWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <EcosystemOrbit  {...template_props}  />
  </div>
  );
};
