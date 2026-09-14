import React from "react";
import { AiComposerShowcase } from "../../remotion-app/src/compositions/ai-composer-showcase";
import type { TemplateProps } from "../../../registry/types";

export const AiComposerShowcaseWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <AiComposerShowcase  />
  );
};
