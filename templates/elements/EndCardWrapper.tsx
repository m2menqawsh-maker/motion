import React from "react";
import { EndCard } from "../../remotion-app/src/remotion/scenes/end-card";
import type { TemplateProps } from "../../../registry/types";

export const EndCardWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <EndCard  {...template_props} 
      title={content?.lines?.[0] || surface?.text || content?.text || undefined} 
      subtitle={content?.lines?.[1] || surface?.subtext || undefined} 
      url={content?.lines?.[2] || undefined} 
    />
  </div>
  );
};
