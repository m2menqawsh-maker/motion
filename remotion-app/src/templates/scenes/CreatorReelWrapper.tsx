import React from "react";
import { CreatorReel } from "../../remotion-app/src/compositions/creator-reel";
import type { TemplateProps } from "../../../registry/types";

export const CreatorReelWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <CreatorReel  {...template_props}  />
  </div>
  );
};
