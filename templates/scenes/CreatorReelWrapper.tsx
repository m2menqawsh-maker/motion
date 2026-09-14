import React from "react";
import { CreatorReel } from "../../remotion-app/src/compositions/creator-reel";
import type { TemplateProps } from "../../../registry/types";

export const CreatorReelWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <CreatorReel  />
  );
};
