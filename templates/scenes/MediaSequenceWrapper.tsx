import React from "react";
import { MediaSequence } from "../../remotion-app/src/remotion/scenes/media-sequence";
import type { TemplateProps } from "../../../registry/types";

export const MediaSequenceWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <MediaSequence  {...template_props} items={content?.items ? content.items.map(i => ({title: i})) : undefined} />
  </div>
  );
};
