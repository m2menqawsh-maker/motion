import React from "react";
import { ReactionBurst } from "../../remotion-app/src/remotion/scenes/reaction-burst";
import type { TemplateProps } from "../../../registry/types";

export const ReactionBurstWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <ReactionBurst  />
  );
};
