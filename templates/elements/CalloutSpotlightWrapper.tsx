import React from "react";
import { CalloutSpotlight } from "../../remotion-app/src/remotion/scenes/callout-spotlight";
import type { TemplateProps } from "../../../registry/types";

export const CalloutSpotlightWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <CalloutSpotlight  {...template_props} title={content?.text || undefined} subtitle={content?.lines?.[0] || undefined} />
  </div>
  );
};
