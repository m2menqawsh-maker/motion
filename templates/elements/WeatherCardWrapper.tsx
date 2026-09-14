import React from "react";
import { WeatherCard } from "../../remotion-app/src/remotion/scenes/weather-card";
import type { TemplateProps } from "../../../registry/types";

export const WeatherCardWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <WeatherCard  />
  );
};
