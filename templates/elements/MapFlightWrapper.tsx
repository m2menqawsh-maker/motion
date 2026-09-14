import React from "react";
import { MapFlight } from "../../remotion-app/src/remotion/scenes/map-flight";
import type { TemplateProps } from "../../../registry/types";

export const MapFlightWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <MapFlight  />
  );
};
