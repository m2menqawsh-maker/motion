import React from "react";
import { CodeReveal } from "../../remotion-app/src/remotion/scenes/code-reveal";
import type { TemplateProps } from "../../../registry/types";

export const CodeRevealWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <CodeReveal title={content?.text || undefined} />
  );
};
