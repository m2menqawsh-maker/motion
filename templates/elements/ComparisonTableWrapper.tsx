import React from "react";
import { ComparisonTable } from "../../remotion-app/src/remotion/scenes/comparison-table";
import type { TemplateProps } from "../../../registry/types";

export const ComparisonTableWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <ComparisonTable title={content?.text || undefined} />
  );
};
