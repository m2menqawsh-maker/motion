import React from "react";
import { DataFlowPipes } from "../../remotion-app/src/remotion/scenes/data-flow-pipes";
import type { TemplateProps } from "../../../registry/types";

export const DataFlowPipesWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <DataFlowPipes  />
  );
};
