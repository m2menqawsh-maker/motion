import React from "react";
import { SearchResultsPopulate } from "../../remotion-app/src/remotion/scenes/search-results-populate";
import type { TemplateProps } from "../../../registry/types";

export const SearchResultsPopulateWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <SearchResultsPopulate  />
  );
};
