import React from "react";
import { LogoWall } from "../../remotion-app/src/remotion/scenes/logo-wall";
import type { TemplateProps } from "../../../registry/types";

export const LogoWallWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <LogoWall title={content?.text || undefined} />
  );
};
