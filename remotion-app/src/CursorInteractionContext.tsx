import { createContext, useContext } from 'react';

export const CursorInteractionContext = createContext<{ onCursorClick?: () => void }>({});

export const useCursorInteraction = () => useContext(CursorInteractionContext);
