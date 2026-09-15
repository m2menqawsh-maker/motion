import React from "react";
import { LogoWall } from "../../remotion-app/src/remotion/scenes/logo-wall";
import type { TemplateProps } from "../../../registry/types";

export const LogoWallWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <LogoWall  {...template_props} title={content?.text || undefined} />
  </div>
  );
};
