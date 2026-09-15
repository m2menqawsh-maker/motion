import React from "react";
import { SearchResultsPopulate } from "../../remotion-app/src/remotion/scenes/search-results-populate";
import type { TemplateProps } from "../../../registry/types";

export const SearchResultsPopulateWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <SearchResultsPopulate  {...template_props}  />
  </div>
  );
};
