import React from "react";
import { CodeAccordion } from "@/remotion/scenes/code-accordion";
import type { TemplateProps } from "@registry/types";

export const CodeAccordionWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <CodeAccordion  {...template_props} title={content?.text || undefined} />
  </div>
  );
};
