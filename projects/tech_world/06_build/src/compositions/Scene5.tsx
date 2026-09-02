import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate, Audio, Sequence, staticFile } from 'remotion';
import React from 'react';

const sceneStartGlobal = 29.4;

export const Scene5: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Entrance spring for the whole UI
  const entrance = spring({
    frame,
    fps,
    config: { damping: 14, mass: 1, stiffness: 100 }
  });

  // "وتابعني" (And follow me) starts at 31.22
  const followStart = (31.22 - sceneStartGlobal) * fps;
  
  // Hover & Click animations
  const hoverSpring = spring({
    frame: frame - followStart,
    fps,
    config: { damping: 14, mass: 1, stiffness: 120 }
  });
  
  const clickSpring = spring({
    frame: frame - (followStart + 15), // Click happens 15 frames after hover
    fps,
    config: { damping: 20, mass: 1, stiffness: 300 }
  });

  // 3D Rotation based on hover
  const rotateX = interpolate(hoverSpring, [0, 1], [15, 0]);
  const rotateY = interpolate(hoverSpring, [0, 1], [-20, 0]);
  const scale = interpolate(clickSpring, [0, 0.5, 1], [1, 0.9, 1.05]); 
  
  // Follow text morph
  const isFollowing = frame > followStart + 15;

  return (
    <AbsoluteFill style={{ backgroundColor: '#050505', perspective: 1200, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
      
      {/* SFX */}
      <Sequence from={0}>
        <Audio src={staticFile("media/sfx_sci_fi_motion_norm.mp3")} volume={0.5} />
      </Sequence>
      <Sequence from={Math.round(followStart + 15)}>
        <Audio src={staticFile("media/sfx_ui_click_norm.mp3")} volume={1} />
        <Audio src={staticFile("media/sfx_pop_norm.mp3")} volume={0.8} />
      </Sequence>

      {/* Background Cyber Grid */}
      <div style={{
        position: 'absolute', width: '200%', height: '200%',
        backgroundImage: 'linear-gradient(rgba(0, 242, 254, 0.1) 4px, transparent 4px), linear-gradient(90deg, rgba(0, 242, 254, 0.1) 4px, transparent 4px)',
        backgroundSize: '150px 150px',
        transform: `rotateX(60deg) translateY(${-(frame * 5)}px)`,
        opacity: 0.2
      }} />

      {/* Main 3D Panel */}
      <div style={{
        width: 800, height: 700,
        backgroundColor: 'rgba(255, 255, 255, 0.02)',
        border: '2px solid rgba(255,255,255,0.05)',
        borderRadius: 60,
        backdropFilter: 'blur(40px)',
        transform: `scale(${interpolate(entrance, [0, 1], [0.5, 1])}) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`,
        opacity: interpolate(entrance, [0, 1], [0, 1]),
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        boxShadow: '0 50px 100px rgba(0,0,0,0.8), inset 0 0 50px rgba(0, 242, 254, 0.1)',
        willChange: 'transform'
      }}>
        
        {/* Profile Avatar */}
        <div style={{
          width: 220, height: 220, borderRadius: '50%',
          background: 'linear-gradient(135deg, #00f2fe 0%, #4facfe 100%)',
          marginBottom: 50,
          display: 'flex', justifyContent: 'center', alignItems: 'center',
          boxShadow: '0 0 80px rgba(0, 242, 254, 0.6)'
        }}>
          <div style={{ width: 200, height: 200, borderRadius: '50%', backgroundColor: '#050505', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
            <span style={{ fontSize: 90 }}>🚀</span>
          </div>
        </div>

        {/* Text */}
        <div style={{ fontFamily: 'Alexandria, sans-serif', fontSize: 70, fontWeight: 900, color: '#fff', marginBottom: 20 }}>
          عالم التقنية
        </div>
        <div style={{ fontFamily: 'Alexandria, sans-serif', fontSize: 40, fontWeight: 600, color: 'rgba(255,255,255,0.4)', marginBottom: 80 }}>
          Tech World 
        </div>

        {/* The Follow Button */}
        <div style={{
          width: 500, height: 120, borderRadius: 60,
          background: isFollowing ? 'linear-gradient(135deg, #00c6ff 0%, #0072ff 100%)' : 'rgba(255,255,255,0.05)',
          border: isFollowing ? 'none' : '3px solid rgba(255,255,255,0.2)',
          display: 'flex', justifyContent: 'center', alignItems: 'center',
          transform: `scale(${scale})`,
          boxShadow: isFollowing ? '0 0 100px rgba(0, 198, 255, 0.8)' : 'none',
          willChange: 'transform'
        }}>
          <span style={{
            fontFamily: 'Alexandria, sans-serif', fontSize: 45, fontWeight: 800,
            color: isFollowing ? '#fff' : 'rgba(255,255,255,0.8)',
            textShadow: isFollowing ? '0 0 20px rgba(255,255,255,0.5)' : 'none'
          }}>
            {isFollowing ? 'تمت المتابعة ✔' : 'متابعة'}
          </span>
        </div>
      </div>

      {/* Mouse Cursor */}
      <div style={{
        position: 'absolute',
        width: 100, height: 100,
        transform: `translate(${interpolate(hoverSpring, [0, 1], [600, 80])}px, ${interpolate(hoverSpring, [0, 1], [800, 240])}px) scale(${interpolate(clickSpring, [0, 0.5, 1], [1, 0.8, 1])})`,
        opacity: interpolate(entrance, [0, 1], [0, 1]),
        zIndex: 10,
        filter: 'drop-shadow(0 20px 20px rgba(0,0,0,0.5))'
      }}>
        {/* Simple SVG Cursor */}
        <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 24 24" fill="#ffffff" stroke="#000000" strokeWidth="1.5">
          <path d="M4 4l7.07 17 2.51-7.39L21 11.07z"/>
        </svg>
      </div>

      {/* Shockwave effect on click */}
      {isFollowing && (
        <div style={{
          position: 'absolute',
          width: 500, height: 120, borderRadius: 60,
          border: '6px solid #00f2fe',
          top: '50%', left: '50%',
          marginTop: 180, // Offset to match button position roughly (height/2 + margins)
          marginLeft: -250,
          transform: `scale(${interpolate(frame - (followStart + 15), [0, 20], [1, 2.5], { extrapolateRight: 'clamp' })})`,
          opacity: interpolate(frame - (followStart + 15), [0, 20], [1, 0], { extrapolateRight: 'clamp' }),
          pointerEvents: 'none'
        }} />
      )}

    </AbsoluteFill>
  );
};
