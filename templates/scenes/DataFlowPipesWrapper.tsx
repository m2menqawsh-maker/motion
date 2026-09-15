import React from "react";
import { DataFlowPipes } from "../../remotion-app/src/remotion/scenes/data-flow-pipes";
import type { TemplateProps } from "../../../registry/types";

export const DataFlowPipesWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <DataFlowPipes  {...template_props}  />
  </div>
  );
};
