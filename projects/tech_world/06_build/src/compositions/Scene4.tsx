import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate, interpolateColors, Audio, Sequence, staticFile } from 'remotion';
import React from 'react';
import timings from '../../../04_timings.json';

const words = timings.segments[6].words;
const sceneStartGlobal = 25.0;

export const Scene4: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Exact timings
  const mutafarijTime = (26.32 - sceneStartGlobal) * fps; // "تظل"
  const tabniTime = (28.08 - sceneStartGlobal) * fps; // "تبدأ"

  // 1. Entrance Springs
  const entrance = spring({ frame, fps, config: { damping: 15, mass: 1.5, stiffness: 100 } });

  // 2. Activation Springs (When the specific word is spoken)
  const card1Active = spring({ frame: frame - mutafarijTime, fps, config: { damping: 12, mass: 1, stiffness: 200 } });
  const card2Active = spring({ frame: frame - tabniTime, fps, config: { damping: 12, mass: 1, stiffness: 200 } });

  // 3. Continuous 3D Float (Majestic Camera pan)
  const floatY1 = Math.sin(frame / 20) * 15;
  const floatY2 = Math.cos(frame / 20) * 15;
  const globalRotateY = interpolate(frame, [0, 150], [10, -10]);

  // "القرار بيدك" Text Pop
  const headerPop = spring({
    frame: frame - ((25.0 - sceneStartGlobal) * fps),
    fps,
    config: { damping: 20, mass: 2, stiffness: 80 }
  });

  return (
    <AbsoluteFill style={{ 
      backgroundColor: '#050505', 
      perspective: 1200, 
      display: 'flex', 
      flexDirection: 'column', 
      justifyContent: 'center', 
      alignItems: 'center' 
    }}>
      
      {/* SFX */}
      <Sequence from={Math.round(mutafarijTime)}>
        <Audio src={staticFile("media/sfx_swipe_norm.mp3")} volume={0.8} />
      </Sequence>
      <Sequence from={Math.round(tabniTime)}>
        <Audio src={staticFile("media/sfx_energy_surge_norm.mp3")} volume={0.8} />
      </Sequence>

      {/* Background Split Lighting */}
      <div style={{
        position: 'absolute', top: 0, left: 0, width: '50%', height: '100%',
        background: 'linear-gradient(90deg, rgba(255,255,255,0.02) 0%, transparent 100%)',
        opacity: interpolate(card1Active, [0, 1], [0, 1])
      }} />
      <div style={{
        position: 'absolute', top: 0, right: 0, width: '50%', height: '100%',
        background: 'linear-gradient(-90deg, rgba(0, 242, 254, 0.05) 0%, transparent 100%)',
        opacity: interpolate(card2Active, [0, 1], [0, 1])
      }} />

      {/* Header */}
      <div style={{
        fontFamily: 'Alexandria, sans-serif',
        fontSize: '90px',
        fontWeight: 900,
        color: '#ffffff',
        transform: `scale(${interpolate(headerPop, [0, 1], [0.5, 1])}) translateY(${interpolate(headerPop, [0, 1], [80, 0])}px)`,
        opacity: interpolate(headerPop, [0, 1], [0, 1]),
        marginBottom: '120px',
        textShadow: '0 0 40px rgba(255,255,255,0.3)',
        zIndex: 10
      }}>
        القرار بيدك
      </div>

      <div style={{ 
        display: 'flex', gap: '100px', width: '90%', justifyContent: 'center', direction: 'rtl',
        transform: `rotateY(${globalRotateY}deg) scale(${interpolate(entrance, [0, 1], [0.8, 1])})`,
        transformStyle: 'preserve-3d'
      }}>
        
        {/* Card 1: Consumer (Dull, Heavy) */}
        <div style={{
          width: '450px',
          height: '550px',
          borderRadius: '50px',
          backgroundColor: 'rgba(20, 20, 20, 0.8)',
          border: '2px solid rgba(255, 255, 255, 0.05)',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          // It pops up slightly when spoken, then settles
          transform: `translateY(${floatY1}px) scale(${interpolate(card1Active, [0, 0.5, 1], [1, 1.05, 1])}) rotateY(15deg)`,
          boxShadow: `0 30px 60px rgba(0,0,0,0.8), inset 0 0 0 ${interpolate(card1Active, [0, 1], [0, 2])}px rgba(255,255,255,0.2)`,
          backdropFilter: 'blur(10px)',
          padding: '40px',
          filter: `grayscale(${interpolate(card1Active, [0, 1], [100, 50])}%)`,
          transition: 'all 0.1s'
        }}>
          {/* Badge */}
          <div style={{
            width: 160, height: 160, borderRadius: 50,
            background: 'linear-gradient(135deg, #2a2a2a 0%, #111 100%)',
            border: '2px solid #333',
            boxShadow: 'inset 0 0 30px rgba(0,0,0,0.8)',
            display: 'flex', justifyContent: 'center', alignItems: 'center',
            marginBottom: '60px'
          }}>
            <svg xmlns="http://www.w3.org/2000/svg" width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.2)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect><line x1="8" y1="21" x2="16" y2="21"></line><line x1="12" y1="17" x2="12" y2="21"></line>
            </svg>
          </div>
          <div style={{
            fontFamily: 'Alexandria, sans-serif', fontSize: '60px', fontWeight: 700,
            color: 'rgba(255, 255, 255, 0.2)', textAlign: 'center',
            opacity: interpolate(card1Active, [0, 1], [0.3, 1])
          }}>
            تظل متفرج
          </div>
        </div>

        {/* Card 2: Creator (Neon, Alive) */}
        <div style={{
          width: '450px',
          height: '550px',
          borderRadius: '50px',
          backgroundColor: interpolateColors(card2Active, [0, 1], ['rgba(0, 242, 254, 0)', 'rgba(0, 242, 254, 0.08)']),
          border: `4px solid rgba(0, 242, 254, ${interpolate(card2Active, [0, 1], [0.1, 1])})`,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          // Massive Pop and push forward
          transform: `translateY(${floatY2}px) scale(${interpolate(card2Active, [0, 0.5, 1], [1, 1.15, 1.1])}) rotateY(-15deg) translateZ(${interpolate(card2Active, [0, 1], [0, 50])}px)`,
          boxShadow: `0 40px 100px rgba(0, 242, 254, ${interpolate(card2Active, [0, 1], [0, 0.4])}), inset 0 0 40px rgba(0, 242, 254, ${interpolate(card2Active, [0, 1], [0, 0.2])})`,
          backdropFilter: 'blur(20px)',
          padding: '40px'
        }}>
          {/* Badge */}
          <div style={{
            width: 160, height: 160, borderRadius: 50,
            background: 'linear-gradient(135deg, #00f2fe 0%, #4facfe 100%)',
            border: '2px solid #fff',
            boxShadow: `0 0 ${interpolate(card2Active, [0, 1], [0, 60])}px rgba(0, 242, 254, 0.8), inset 0 0 20px rgba(255,255,255,0.5)`,
            display: 'flex', justifyContent: 'center', alignItems: 'center',
            position: 'relative',
            marginBottom: '60px',
            transform: `rotate(${interpolate(card2Active, [0, 1], [0, -10])}deg)`
          }}>
            <svg xmlns="http://www.w3.org/2000/svg" width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="#ffffff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ filter: 'drop-shadow(0 0 10px rgba(255,255,255,0.8))' }}>
              <polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline>
            </svg>
          </div>
          <div style={{
            fontFamily: 'Alexandria, sans-serif', fontSize: '60px', fontWeight: 900,
            color: '#ffffff', textAlign: 'center',
            textShadow: `0 0 ${interpolate(card2Active, [0, 1], [0, 30])}px #00f2fe`,
            opacity: interpolate(card2Active, [0, 1], [0.3, 1])
          }}>
            تبني وتجرب
          </div>
        </div>

      </div>
    </AbsoluteFill>
  );
};
