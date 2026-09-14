import React from "react";
import { PollOverlay } from "../../remotion-app/src/remotion/scenes/poll-overlay";
import type { TemplateProps } from "../../../registry/types";

export const PollOverlayWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <PollOverlay  />
  );
};
