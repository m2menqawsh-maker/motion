import React from "react";
import { WeatherCard } from "@/remotion/scenes/weather-card";
import type { TemplateProps } from "@registry/types";

export const WeatherCardWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <WeatherCard  {...template_props}  />
  </div>
  );
};
