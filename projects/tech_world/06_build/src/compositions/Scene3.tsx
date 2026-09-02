import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate, Audio, Sequence, staticFile } from 'remotion';
import React from 'react';
import timings from '../../../04_timings.json';

const words = timings.segments[5].words; // أكبر المشاريع...
const sceneStartGlobal = 19.84;

export const Scene3: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Implosion Flash (frames 0 to 15)
  const flashOpacity = interpolate(frame, [0, 10], [1, 0], { extrapolateRight: 'clamp' });
  const flashScale = interpolate(frame, [0, 10], [10, 0], { extrapolateRight: 'clamp' });

  // Camera Zoom Out at the very end
  // The scene is around 155 frames long. Let's start zooming out at frame 110.
  const cameraZoomOut = spring({
    frame: frame - 110,
    fps,
    config: { damping: 15, mass: 1.5, stiffness: 80 }
  });

  // Global scale starts zoomed in, then zooms out
  const globalScale = interpolate(cameraZoomOut, [0, 1], [1.3, 1]);
  const globalY = interpolate(cameraZoomOut, [0, 1], [50, 0]);

  // Slow continuous pan & rotation for dynamic 3D feel
  const panX = Math.sin(frame / 40) * 20;
  const panY = Math.cos(frame / 40) * 10;
  const rotateX = Math.sin(frame / 50) * 5;
  const rotateY = Math.cos(frame / 50) * 5;

  return (
    <AbsoluteFill style={{ backgroundColor: '#050505', perspective: 1200, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
      
      {/* Implosion Flash Effect */}
      <Sequence from={0}>
        <Audio src={staticFile("media/sfx_pop_norm.mp3")} volume={1} />
      </Sequence>
      
      {/* "بسيطة" word is the last word in the segment, let's play the click/zap when it appears */}
      <Sequence from={Math.round((words[words.length - 1].start - sceneStartGlobal) * fps)}>
        <Audio src={staticFile("media/sfx_ui_click_norm.mp3")} volume={0.8} />
      </Sequence>

      <AbsoluteFill style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 20 }}>
        <div style={{
          width: 500, height: 500, borderRadius: '50%',
          backgroundColor: '#00f2fe',
          opacity: flashOpacity,
          transform: `scale(${flashScale})`,
          boxShadow: '0 0 200px #00f2fe',
          pointerEvents: 'none'
        }} />
      </AbsoluteFill>

      {/* Grid Background */}
      <div style={{
        position: 'absolute', width: '200%', height: '200%',
        backgroundImage: 'linear-gradient(rgba(0, 242, 254, 0.05) 2px, transparent 2px), linear-gradient(90deg, rgba(0, 242, 254, 0.05) 2px, transparent 2px)',
        backgroundSize: '120px 120px',
        transform: `translateZ(-500px) rotateX(60deg) translateY(${-(frame * 2)}px)`,
        opacity: 0.6
      }} />

      {/* Massive Words */}
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        justifyContent: 'center',
        alignItems: 'center',
        alignContent: 'center',
        width: '90%',
        gap: '40px',
        direction: 'rtl',
        transform: `scale(${globalScale}) translate(${panX}px, ${panY + globalY}px) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`,
        transformStyle: 'preserve-3d',
        zIndex: 10
      }}>
        {words.map((w, i) => {
          const wordStartLocal = (w.start - sceneStartGlobal) * fps;
          
          const pop = spring({
            frame: frame - wordStartLocal,
            fps,
            config: { damping: 14, mass: 1, stiffness: 150 }
          });
          
          const wordTrimmed = w.word.trim();
          const isHighlight = wordTrimmed === 'التقنية' || wordTrimmed === 'بسيطة';
          const isPill = wordTrimmed === 'بسيطة';
          const isSpecial = i < 3; // "أكبر المشاريع التقنية"

          if (frame < wordStartLocal) return null;
          
          return (
            <span
              key={i}
              style={{
                fontFamily: 'Alexandria, sans-serif',
                fontSize: isSpecial ? '120px' : '90px',
                fontWeight: 900,
                color: isHighlight ? '#00f2fe' : '#ffffff',
                background: isPill ? 'rgba(0, 242, 254, 0.15)' : 'none',
                border: isPill ? '6px solid #00f2fe' : 'none',
                borderRadius: isPill ? '50px' : '0px',
                padding: isPill ? '10px 50px' : '0px',
                transform: `scale(${interpolate(pop, [0, 1], [0.3, 1])}) translateZ(${interpolate(pop, [0, 1], [300, 0])}px)`,
                opacity: interpolate(pop, [0, 1], [0, 1]),
                textShadow: isHighlight && !isPill ? '0 0 50px rgba(0, 242, 254, 0.8)' : '0 10px 30px rgba(0,0,0,0.8)',
                boxShadow: isPill ? '0 0 60px rgba(0, 242, 254, 0.5), inset 0 0 20px rgba(0, 242, 254, 0.5)' : 'none',
                willChange: 'transform'
              }}
            >
              {w.word}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
