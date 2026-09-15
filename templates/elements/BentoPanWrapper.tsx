import React from "react";
import { BentoPan } from "../../remotion-app/src/compositions/bento-pan";
import type { TemplateProps } from "../../../registry/types";

export const BentoPanWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <BentoPan  {...template_props}  />
  </div>
  );
};
