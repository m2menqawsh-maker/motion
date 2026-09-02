import React from 'react';
import { AbsoluteFill, Sequence, staticFile, useCurrentFrame, interpolate, spring, useVideoConfig } from 'remotion';
import { TrackingIn } from '../../premium-templates/typography/tracking-in/TrackingIn';
import { Highlight } from '../../engine/primitives/Highlight';

export const Scene1: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Scale and entrance animations
  const cardScale = spring({
    frame: frame - 20,
    fps,
    config: { stiffness: 220, damping: 20 }
  });

  const planCardScale = spring({
    frame: frame - 80,
    fps,
    config: { stiffness: 220, damping: 20 }
  });

  const glowPulse = interpolate(
    Math.sin(frame / 6),
    [-1, 1],
    [0.3, 0.7]
  );

  return (
    <AbsoluteFill style={{ direction: 'rtl', fontFamily: 'Alexandria, sans-serif' }}>
      {/* Shot 1.1: 0 to 80 frames (0.00s - 2.66s) */}
      <Sequence from={0} durationInFrames={80}>
        <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', padding: '60px' }}>
          
          {/* Top Badge */}
          <div style={{
            position: 'absolute',
            top: 180,
            background: 'rgba(0, 229, 255, 0.1)',
            border: '1px solid rgba(0, 229, 255, 0.4)',
            borderRadius: '50px',
            padding: '14px 36px',
            color: '#00E5FF',
            fontSize: 28,
            fontWeight: 700,
            letterSpacing: '1px',
            boxShadow: '0 0 25px rgba(0, 229, 255, 0.25)',
            willChange: 'transform'
          }}>
            ⚡ تحدي البرمجة السريع
          </div>

          {/* Sub-shot: "أعطني" */}
          <Sequence from={0} durationInFrames={24}>
            <div style={{
              fontSize: 90,
              fontWeight: 900,
              color: '#FFFFFF',
              textShadow: '0 0 30px rgba(255,255,255,0.4)',
              willChange: 'transform'
            }}>
              أعطني
            </div>
          </Sequence>

          {/* Sub-shot: "45 ثانية" in a 3D Glassmorphism Hero Card */}
          <Sequence from={20} durationInFrames={60}>
            <div style={{
              transform: `scale(${Math.max(0, cardScale)})`,
              background: 'rgba(18, 20, 32, 0.75)',
              backdropFilter: 'blur(20px)',
              border: '2px solid rgba(0, 229, 255, 0.6)',
              borderRadius: '36px',
              padding: '60px 80px',
              boxShadow: `0 20px 60px rgba(0, 0, 0, 0.6), 0 0 40px rgba(0, 229, 255, ${glowPulse})`,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '20px',
              willChange: 'transform'
            }}>
              <TrackingIn
                text="45 ثانية"
                fontSize={110}
                color="#00E5FF"
                delay={0}
                duration={25}
                tracking={0}
                fromTracking={0.4}
                blur={false}
              />
              <div style={{
                color: '#94A3B8',
                fontSize: 32,
                fontWeight: 600
              }}>
                فقط من وقتك
              </div>
            </div>
          </Sequence>

        </AbsoluteFill>
      </Sequence>

      {/* Shot 1.2: 80 to 184 frames (2.66s - 6.14s) */}
      <Sequence from={80} durationInFrames={104}>
        <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', padding: '60px' }}>
          
          {/* Main Promise Hero Card */}
          <div style={{
            transform: `scale(${Math.max(0, planCardScale)})`,
            background: 'rgba(18, 20, 32, 0.85)',
            backdropFilter: 'blur(24px)',
            border: '2px solid rgba(139, 92, 246, 0.6)',
            borderRadius: '40px',
            padding: '70px 60px',
            boxShadow: '0 25px 70px rgba(0, 0, 0, 0.7), 0 0 50px rgba(139, 92, 246, 0.3)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '30px',
            maxWidth: '900px',
            width: '100%',
            willChange: 'transform'
          }}>
            {/* Tag / Icon Header */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '16px',
              background: 'rgba(139, 92, 246, 0.15)',
              border: '1px solid rgba(139, 92, 246, 0.4)',
              borderRadius: '30px',
              padding: '10px 28px'
            }}>
              <span style={{ fontSize: 30 }}>🚀</span>
              <span style={{ color: '#C4B5FD', fontSize: 26, fontWeight: 700 }}>خارطة طريق حقيقية</span>
            </div>

            {/* Promise Headline */}
            <div style={{
              fontSize: 76,
              fontWeight: 900,
              color: '#FFFFFF',
              textAlign: 'center',
              lineHeight: 1.3
            }}>
              وسأعطيك <span style={{ color: '#00E5FF' }}>خطة</span>
            </div>

            {/* Highlighted Goal */}
            <div style={{
              fontSize: 64,
              fontWeight: 800,
              color: '#A78BFA',
              textAlign: 'center'
            }}>
              <Highlight color="rgba(139, 92, 246, 0.35)">
                لتعلم البرمجة
              </Highlight>
            </div>

            {/* Sub-badge */}
            <div style={{
              marginTop: '10px',
              color: '#94A3B8',
              fontSize: 28,
              fontWeight: 600
            }}>
              في 30 يوماً فقط
            </div>
          </div>

        </AbsoluteFill>
      </Sequence>
    </AbsoluteFill>
  );
};
