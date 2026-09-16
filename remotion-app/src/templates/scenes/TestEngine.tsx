import React from 'react';
import { AbsoluteFill, Sequence } from 'remotion';
import { AppShell } from '../../engine/primitives/app-ui/AppShell';
import { Cursor } from '../../engine/cursor/Cursor';
import { UIStateProvider } from '../../engine/ui-state/UIStateProvider';

export const TestEngine: React.FC<{ surface: any, content: any }> = ({ surface }) => {
  return (
    <AbsoluteFill style={{ backgroundColor: 'white' }}>
      <UIStateProvider>
        <AppShell sidebar={<div style={{padding: 20}}>Sidebar</div>} topBar={<div style={{padding: 20}}>TopBar</div>}>
          <div data-cursor-target="btn" style={{ padding: 50, border: '1px solid black', margin: 50, width: 200, height: 100, backgroundColor: '#eee' }}>
             {surface.text || "Test Content"}
          </div>
        </AppShell>
        <Cursor actions={[
          { at: 0, action: "idle", position: {x: 100, y: 100} }, 
          { at: 10, action: "moveTo", target: "btn", duration: 30, anchor: "center" },
          { at: 50, action: "click", target: "btn" }
        ]} />
      </UIStateProvider>
    </AbsoluteFill>
  );
};
