import React from "react";
import { AiComposerShowcase } from "@/compositions/ai-composer-showcase";
import type { TemplateProps } from "@registry/types";

export const AiComposerShowcaseWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <AiComposerShowcase  {...template_props}  />
  </div>
  );
};
