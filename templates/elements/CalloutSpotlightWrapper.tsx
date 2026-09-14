import React from "react";
import { CalloutSpotlight } from "../../remotion-app/src/remotion/scenes/callout-spotlight";
import type { TemplateProps } from "../../../registry/types";

export const CalloutSpotlightWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <CalloutSpotlight title={content?.text || undefined} subtitle={content?.lines?.[0] || undefined} />
  );
};
