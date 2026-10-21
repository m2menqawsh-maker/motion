import React from "react";
import { MapFlight } from "@/remotion/scenes/map-flight";
import type { TemplateProps } from "@registry/types";

export const MapFlightWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <MapFlight  {...template_props}  />
  </div>
  );
};
