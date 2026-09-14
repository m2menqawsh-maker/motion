import React from "react";
import { ZoomPanFrame } from "../../remotion-app/src/remotion/scenes/zoom-pan-frame";
import type { TemplateProps } from "../../../registry/types";

export const ZoomPanFrameWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <ZoomPanFrame label={content?.text || undefined} />
  );
};
