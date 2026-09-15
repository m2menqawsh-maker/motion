import React from "react";
import { CommitGraph } from "../../remotion-app/src/remotion/scenes/commit-graph";
import type { TemplateProps } from "../../../registry/types";

export const CommitGraphWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <CommitGraph  {...template_props}  />
  </div>
  );
};
