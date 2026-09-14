import React from "react";
import { CodeDiffWipe } from "../../remotion-app/src/remotion/scenes/code-diff-wipe";
import type { TemplateProps } from "../../../registry/types";

export const CodeDiffWipeWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <CodeDiffWipe title={content?.text || undefined} />
  );
};
