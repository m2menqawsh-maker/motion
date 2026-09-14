import React from "react";
import { CommitGraph } from "../../remotion-app/src/remotion/scenes/commit-graph";
import type { TemplateProps } from "../../../registry/types";

export const CommitGraphWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <CommitGraph  />
  );
};
