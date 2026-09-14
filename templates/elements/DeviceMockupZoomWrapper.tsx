import React from "react";
import { DeviceMockupZoom } from "../../remotion-app/src/remotion/scenes/device-mockup-zoom";
import type { TemplateProps } from "../../../registry/types";

export const DeviceMockupZoomWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <DeviceMockupZoom title={content?.text || undefined} subtitle={content?.lines?.[0] || undefined} />
  );
};
