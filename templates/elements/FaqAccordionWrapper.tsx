import React from "react";
import { FaqAccordion } from "../../remotion-app/src/remotion/scenes/faq-accordion";
import type { TemplateProps } from "../../../registry/types";

export const FaqAccordionWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <FaqAccordion items={content?.items ? content.items.map(i => ({title: i})) : undefined} title={content?.text || undefined} />
  );
};
