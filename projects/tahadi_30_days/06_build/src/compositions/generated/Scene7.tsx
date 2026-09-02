import React from 'react';
import { AbsoluteFill, Sequence, spring, useCurrentFrame, useVideoConfig } from 'remotion';

export const Scene7: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Chat window pops up
  const chatScale = spring({
    fps,
    frame,
    config: { damping: 14, mass: 1, stiffness: 120 }
  });

  // "لا ليكتب الكود عنك" -> starts around 42.66s. 
  // Scene starts at 38.00 (frame 1140). So it's 4.66s into the scene = 140 frames.
  const crossScale = spring({
    fps,
    frame: frame - 140,
    config: { damping: 12, mass: 2, stiffness: 150 }
  });

  return (
    <AbsoluteFill>
      <Sequence from={0} durationInFrames={210}>
        <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center' }}>
          
          {/* AI Chat Window */}
          <div style={{
            width: '800px',
            height: '500px',
            background: 'rgba(255, 255, 255, 0.05)',
            backdropFilter: 'blur(30px)',
            borderRadius: '30px',
            border: '2px solid rgba(0, 229, 255, 0.3)',
            boxShadow: '0 30px 60px rgba(0,0,0,0.8), 0 0 50px rgba(0, 229, 255, 0.1)',
            transform: `scale(${chatScale})`,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden'
          }}>
            {/* Header */}
            <div style={{
              height: '60px',
              borderBottom: '1px solid rgba(255,255,255,0.1)',
              display: 'flex',
              alignItems: 'center',
              padding: '0 30px',
              fontFamily: 'Alexandria',
              color: '#00e5ff',
              fontSize: '24px',
              fontWeight: 'bold',
              direction: 'rtl'
            }}>
              مساعد الذكاء الاصطناعي ✨
            </div>
            
            {/* Chat Body */}
            <div style={{ padding: '30px', display: 'flex', flexDirection: 'column', gap: '20px', direction: 'rtl' }}>
              {/* User Message */}
              <div style={{
                alignSelf: 'flex-start',
                background: 'rgba(255,255,255,0.1)',
                padding: '20px 30px',
                borderRadius: '20px 20px 0 20px',
                fontFamily: 'Alexandria',
                color: '#fff',
                fontSize: '28px'
              }}>
                لدي خطأ في هذا الكود...
              </div>

              {/* AI Response */}
              <div style={{
                alignSelf: 'flex-end',
                background: 'rgba(0, 229, 255, 0.2)',
                border: '1px solid rgba(0, 229, 255, 0.4)',
                padding: '20px 30px',
                borderRadius: '20px 20px 20px 0',
                fontFamily: 'Alexandria',
                color: '#fff',
                fontSize: '28px',
                maxWidth: '80%'
              }}>
                الخطأ يكمن في المتغير `x`، عليك تعريفه أولاً باستخدام `let` أو `const` قبل استخدامه.
              </div>
            </div>
          </div>

          {/* Big Red Cross overlaying the chat at frame 140 */}
          <div style={{
            position: 'absolute',
            fontFamily: 'sans-serif',
            fontSize: '500px',
            color: '#FF0055',
            fontWeight: 'bold',
            textShadow: '0 0 100px rgba(255, 0, 85, 0.8)',
            transform: `scale(${crossScale}) rotate(-10deg)`,
            pointerEvents: 'none'
          }}>
            X
          </div>

        </AbsoluteFill>
      </Sequence>
    </AbsoluteFill>
  );
};
