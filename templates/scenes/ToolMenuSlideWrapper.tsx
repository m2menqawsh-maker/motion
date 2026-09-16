import React from "react";
import { ToolMenuSlide } from "@/compositions/tool-menu-slide";
import type { TemplateProps } from "@registry/types";

export const ToolMenuSlideWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <ToolMenuSlide  {...template_props}  />
  </div>
  );
};
