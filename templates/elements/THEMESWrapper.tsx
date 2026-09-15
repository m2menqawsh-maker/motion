import React from "react";
import { THEMES } from "../../remotion-app/src/remotion/scenes/v0";
import type { TemplateProps } from "../../../registry/types";

export const THEMESWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <THEMES  {...template_props}  />
  </div>
  );
};
