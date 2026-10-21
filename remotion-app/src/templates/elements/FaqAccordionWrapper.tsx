import React from "react";
import { FaqAccordion } from "@/remotion/scenes/faq-accordion";
import type { TemplateProps } from "@registry/types";

export const FaqAccordionWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <FaqAccordion  {...template_props} items={content?.items ? content.items.map((i: any) => ({title: i})) : undefined} title={content?.text || undefined} />
  </div>
  );
};
