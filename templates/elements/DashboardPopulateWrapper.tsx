import React from "react";
import { DashboardPopulate } from "../../remotion-app/src/compositions/dashboard-populate";
import type { TemplateProps } from "../../../registry/types";

export const DashboardPopulateWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <DashboardPopulate  />
  );
};
