import React from "react";
import { HeroLoop } from "../../remotion-app/src/compositions/hero-loop";
import type { TemplateProps } from "../../../registry/types";

export const HeroLoopWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <HeroLoop  {...template_props}  />
  </div>
  );
};
