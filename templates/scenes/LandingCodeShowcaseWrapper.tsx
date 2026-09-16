import React from "react";
import { LandingCodeShowcase } from "@/compositions/landing-code-showcase";
import type { TemplateProps } from "@registry/types";

export const LandingCodeShowcaseWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <LandingCodeShowcase  {...template_props}  />
  </div>
  );
};
