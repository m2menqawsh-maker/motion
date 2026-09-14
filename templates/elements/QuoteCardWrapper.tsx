import React from "react";
import { QuoteCard } from "../../remotion-app/src/remotion/scenes/quote-card";
import type { TemplateProps } from "../../../registry/types";

export const QuoteCardWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <QuoteCard  />
  );
};
