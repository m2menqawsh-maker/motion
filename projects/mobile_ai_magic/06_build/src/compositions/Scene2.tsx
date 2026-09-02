import React from 'react';
import { AbsoluteFill, Sequence, useVideoConfig, useCurrentFrame, spring, interpolate, OffthreadVideo, Audio, staticFile } from 'remotion';
import { TrackingIn } from '@/templates/elements/typography/tracking-in/TrackingIn';
import { loadFont } from "@remotion/google-fonts/Cairo";

const { fontFamily } = loadFont();

const SocialIcon: React.FC<{ progress: number, color: string, path: string, delay: number }> = ({ progress, color, path, delay }) => {
  const scale = interpolate(progress, [0, 1], [0.5, 1], { extrapolateRight: 'clamp' });
  const glowOpacity = interpolate(progress, [0, 0.5, 1], [0, 1, 0.6], { extrapolateRight: 'clamp' });

  return (
    <div style={{
      position: 'relative',
      transform: `scale(${scale})`,
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      margin: '0 30px'
    }}>
      {/* Light Glow */}
      <div style={{
        position: 'absolute',
        width: 150,
        height: 150,
        borderRadius: '50%',
        backgroundColor: color,
        filter: 'blur(50px)',
        opacity: glowOpacity,
        zIndex: 1
      }} />
      
      {/* Colorful Icon Wrapper */}
      <div style={{
        zIndex: 2,
        background: `linear-gradient(135deg, ${color}, #222)`,
        padding: 30,
        borderRadius: 30,
        boxShadow: '0 20px 50px rgba(0,0,0,0.5)',
        border: '4px solid rgba(255,255,255,0.2)'
      }}>
        <svg 
          width="80" 
          height="80" 
          viewBox="0 0 24 24" 
          fill="white" 
        >
          <path d={path} />
        </svg>
      </div>
    </div>
  );
};

const SOCIAL_PATHS = [
  // Facebook
  "M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z",
  // Instagram
  "M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37zm1.5-4.87h.01M6.5 6.5h11A5 5 0 0 1 22.5 12v11a5 5 0 0 1-5 5h-11a5 5 0 0 1-5-5V12a5 5 0 0 1 5-5z",
  // Twitter
  "M23 3a10.9 10.9 0 0 1-3.14 1.53 4.48 4.48 0 0 0-7.86 3v1A10.66 10.66 0 0 1 3 4s-4 9 5 13a11.64 11.64 0 0 1-7 2c9 5 20 0 20-11.5a4.5 4.5 0 0 0-.08-.83A7.72 7.72 0 0 0 23 3z"
];
const SOCIAL_COLORS = ["#1877F2", "#E4405F", "#1DA1F2"];

export const Scene2: React.FC = () => {
  const { fps } = useVideoConfig();
  const frame = useCurrentFrame();

  const iconProgress1 = spring({ frame: frame - 10, fps, config: { damping: 12 }, durationInFrames: 30 });
  const iconProgress2 = spring({ frame: frame - 15, fps, config: { damping: 12 }, durationInFrames: 30 });
  const iconProgress3 = spring({ frame: frame - 20, fps, config: { damping: 12 }, durationInFrames: 30 });

  return (
    <AbsoluteFill style={{ backgroundColor: 'black' }}>
      <OffthreadVideo 
        src={staticFile('media/bg_ai_final.mp4')} 
        style={{ width: '100%', height: '100%', objectFit: 'cover', opacity: 0.5 }} 
      />
      
      <Audio src={staticFile('media/sentence_002_norm.wav')} />
      <Sequence from={10}>
        <Audio src={staticFile('media/pop_norm.wav')} volume={0.8} />
      </Sequence>
      
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        width: '100%',
        height: '100%',
        color: 'white',
        fontFamily
      }}>
        <div style={{ position: 'absolute', top: '25%', width: '100%', display: 'flex', justifyContent: 'center' }}>
          <SocialIcon progress={iconProgress1} color={SOCIAL_COLORS[0]} path={SOCIAL_PATHS[0]} delay={0} />
          <SocialIcon progress={iconProgress2} color={SOCIAL_COLORS[1]} path={SOCIAL_PATHS[1]} delay={5} />
          <SocialIcon progress={iconProgress3} color={SOCIAL_COLORS[2]} path={SOCIAL_PATHS[2]} delay={10} />
        </div>

        <Sequence from={35}>
          <div style={{ position: 'absolute', top: '60%', width: '100%', display: 'flex', justifyContent: 'center', direction: 'rtl', willChange: 'transform' }}>
            <TrackingIn 
              text="بتستخدمه" 
              delay={0} 
              duration={15} 
              color="#fff" 
              fromTracking={0.2} 
              tracking={0} 
              blur={true} 
              fontSize={120} 
              fontWeight="900" 
            />
          </div>
        </Sequence>
        
        <Sequence from={55}>
          <div style={{ position: 'absolute', top: '70%', width: '100%', display: 'flex', justifyContent: 'center', direction: 'rtl', willChange: 'transform' }}>
            <TrackingIn 
              text="كمستهلك بس!" 
              delay={0} 
              duration={20} 
              color="#ff007f" 
              fromTracking={0.1} 
              tracking={0} 
              blur={true} 
              fontSize={140} 
              fontWeight="900" 
            />
          </div>
        </Sequence>
      </div>
    </AbsoluteFill>
  );
};
