import React, { ReactNode } from "react";

export interface TextToolbarValues {
  fontSize: number;
  fontWeight: number;
  letterSpacing: number;
  lineHeight: number;
  color: string;
}

export interface InlineEditProps {
  value: string;
  onChange: (val: string) => void;
  style?: React.CSSProperties;
  children?: ReactNode;
}

export const InlineEdit: React.FC<InlineEditProps> = ({ value, style, children }) => {
  if (!children) {
    return <span style={style}>{value}</span>;
  }
  return <>{children}</>;
};

export interface TextToolbarProps {
  values: TextToolbarValues;
  onChange: (vals: Partial<TextToolbarValues>) => void;
  style?: React.CSSProperties;
}

export const TextToolbar: React.FC<TextToolbarProps> = ({ style }) => {
  return <div style={{ ...style, display: "none" }} aria-hidden="true" />;
};

export const persistUpdate = (updater: (prev: any) => any) => {};
export const getPendingRevision = () => 0;
export const applyPendingEdits = (path: any) => path;
