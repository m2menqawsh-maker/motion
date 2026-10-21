import React from "react";
import { FormFillSequence } from "@/remotion/scenes/form-fill-sequence";
import type { TemplateProps } from "@registry/types";

export const FormFillSequenceWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <FormFillSequence  {...template_props} title={content?.text || undefined} subtitle={content?.lines?.[0] || undefined} />
  </div>
  );
};
