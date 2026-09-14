import React from "react";
import { CodeAccordion } from "../../remotion-app/src/remotion/scenes/code-accordion";
import type { TemplateProps } from "../../../registry/types";

export const CodeAccordionWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <CodeAccordion title={content?.text || undefined} />
  );
};
