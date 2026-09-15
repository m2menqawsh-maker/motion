import React from "react";
import { DataStory } from "../../remotion-app/src/compositions/data-story";
import type { TemplateProps } from "../../../registry/types";

export const DataStoryWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <DataStory  {...template_props} title={content?.text || undefined} subtitle={content?.lines?.[0] || undefined} />
  </div>
  );
};
