import React from "react";
import { ImageExpand } from "../../remotion-app/src/compositions/image-expand";
import type { TemplateProps } from "../../../registry/types";

export const ImageExpandWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <ImageExpand title={content?.text || undefined} subtitle={content?.lines?.[0] || undefined} />
  );
};
