import React from "react";
import { FormFillSequence } from "../../remotion-app/src/remotion/scenes/form-fill-sequence";
import type { TemplateProps } from "../../../registry/types";

export const FormFillSequenceWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <FormFillSequence title={content?.text || undefined} subtitle={content?.lines?.[0] || undefined} />
  );
};
