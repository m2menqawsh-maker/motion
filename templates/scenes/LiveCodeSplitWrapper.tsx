import React from "react";
import { LiveCodeSplit } from "../../remotion-app/src/compositions/live-code-split";
import type { TemplateProps } from "../../../registry/types";

export const LiveCodeSplitWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <LiveCodeSplit  />
  );
};
