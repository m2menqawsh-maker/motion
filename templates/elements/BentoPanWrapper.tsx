import React from "react";
import { BentoPan } from "../../remotion-app/src/compositions/bento-pan";
import type { TemplateProps } from "../../../registry/types";

export const BentoPanWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <BentoPan  />
  );
};
