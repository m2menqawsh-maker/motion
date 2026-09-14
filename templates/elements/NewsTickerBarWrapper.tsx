import React from "react";
import { NewsTickerBar } from "../../remotion-app/src/remotion/scenes/news-ticker-bar";
import type { TemplateProps } from "../../../registry/types";

export const NewsTickerBarWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <NewsTickerBar  />
  );
};
