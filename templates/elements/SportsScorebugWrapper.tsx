import React from "react";
import { SportsScorebug } from "../../remotion-app/src/remotion/scenes/sports-scorebug";
import type { TemplateProps } from "../../../registry/types";

export const SportsScorebugWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <SportsScorebug  {...template_props}  />
  </div>
  );
};
