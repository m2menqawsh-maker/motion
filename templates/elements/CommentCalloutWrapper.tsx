import React from "react";
import { CommentCallout } from "../../remotion-app/src/remotion/scenes/comment-callout";
import type { TemplateProps } from "../../../registry/types";

export const CommentCalloutWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <CommentCallout  />
  );
};
