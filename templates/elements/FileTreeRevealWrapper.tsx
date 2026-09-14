import React from "react";
import { FileTreeReveal } from "../../remotion-app/src/remotion/scenes/file-tree-reveal";
import type { TemplateProps } from "../../../registry/types";

export const FileTreeRevealWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <FileTreeReveal title={content?.text || undefined} />
  );
};
