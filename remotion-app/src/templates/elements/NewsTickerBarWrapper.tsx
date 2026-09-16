import React from "react";
import { NewsTickerBar } from "@/remotion/scenes/news-ticker-bar";
import type { TemplateProps } from "@registry/types";

export const NewsTickerBarWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <NewsTickerBar  {...template_props}  />
  </div>
  );
};
