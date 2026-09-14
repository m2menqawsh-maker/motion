import React from "react";
import { BrowserFlow } from "../../remotion-app/src/compositions/browser-flow";
import type { TemplateProps } from "../../../registry/types";

export const BrowserFlowWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <BrowserFlow url={content?.lines?.[1] || undefined} title={content?.text || undefined} />
  );
};
