import React, { createContext, useContext, useState, useCallback, ReactNode } from "react";

export interface CursorInteractionState {
  onCursorClick?: () => void;
  setOnCursorClick: (fn: (() => void) | undefined) => void;
}

const defaultState: CursorInteractionState = {
  onCursorClick: undefined,
  setOnCursorClick: () => {
    console.warn("CursorInteractionProvider is missing from the tree.");
  },
};

const CursorInteractionContext = createContext<CursorInteractionState>(defaultState);

export const CursorInteractionProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [onCursorClick, setOnCursorClickState] = useState<(() => void) | undefined>(undefined);

  const setOnCursorClick = useCallback((fn: (() => void) | undefined) => {
    setOnCursorClickState(() => fn);
  }, []);

  return (
    <CursorInteractionContext.Provider value={{ onCursorClick, setOnCursorClick }}>
      {children}
    </CursorInteractionContext.Provider>
  );
};

export function useCursorInteraction(): CursorInteractionState {
  return useContext(CursorInteractionContext);
}
