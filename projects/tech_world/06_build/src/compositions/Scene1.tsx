import React from 'react';
import { AbsoluteFill, Sequence, Series, Audio, staticFile, OffthreadVideo } from 'remotion';
import { KenBurns } from '../templates/scenes/product/ken-burns/KenBurns';
import { Captions } from '../templates/elements/captions/captions/Captions';
import { Highlight } from '../engine/primitives/Highlight';
import { DeviceMockupZoom } from '../remotion/scenes/device-mockup-zoom';
import { loadFont } from "@remotion/google-fonts/Alexandria";
import timings from '../../../04_timings.json';

const HeartIcon = () => (
  <svg viewBox="0 0 24 24" width="36" height="36" stroke="white" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>
  </svg>
);

const CommentIcon = () => (
  <svg viewBox="0 0 24 24" width="36" height="36" stroke="white" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path>
  </svg>
);

const ShareIcon = () => (
  <svg viewBox="0 0 24 24" width="36" height="36" stroke="white" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
    <line x1="22" y1="2" x2="11" y2="13"></line>
    <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
  </svg>
);

const MoreIcon = () => (
  <svg viewBox="0 0 24 24" width="36" height="36" stroke="white" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="2"></circle>
    <circle cx="12" cy="5" r="2"></circle>
    <circle cx="12" cy="19" r="2"></circle>
  </svg>
);

const InstagramReelsUI: React.FC = () => {
  return (
    <AbsoluteFill style={{ color: 'white' }}>
      <OffthreadVideo 
        src={staticFile("media/pexels_video_12172194_intra.mp4")} 
        style={{ objectFit: 'cover', width: '100%', height: '100%' }}
      />
      <div style={{ position: 'absolute', inset: 0, backgroundColor: 'rgba(0,0,0,0.1)' }} />

      {/* Top Header */}
      <div style={{ position: 'absolute', top: 60, left: 30, fontSize: 32, fontWeight: 'bold' }}>Reels</div>
      
      {/* Right Sidebar */}
      <div style={{ position: 'absolute', bottom: 160, right: 25, display: 'flex', flexDirection: 'column', gap: 35, alignItems: 'center' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
          <HeartIcon />
          <span style={{ fontSize: 16, fontWeight: 'bold' }}>12.4K</span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
          <CommentIcon />
          <span style={{ fontSize: 16, fontWeight: 'bold' }}>342</span>
        </div>
        <ShareIcon />
        <MoreIcon />
        <div style={{ width: 48, height: 48, borderRadius: 10, border: '3px solid white', overflow: 'hidden', marginTop: 15 }}>
           <img src="https://i.pravatar.cc/100" style={{ width: '100%', height: '100%' }} />
        </div>
      </div>

      {/* Bottom User Info */}
      <div style={{ position: 'absolute', bottom: 60, left: 30, display: 'flex', flexDirection: 'column', gap: 15 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 15 }}>
          <img src="https://i.pravatar.cc/100" style={{ width: 56, height: 56, borderRadius: '50%', border: '3px solid #4facfe' }} />
          <span style={{ fontSize: 24, fontWeight: 'bold' }}>tech_world</span>
          <span style={{ fontSize: 18, border: '2px solid white', borderRadius: 8, padding: '4px 14px', fontWeight: 'bold' }}>Follow</span>
        </div>
        <div style={{ fontSize: 22, maxWidth: '85%' }}>
          أكبر المشاريع التقنية بدأت بخطوة بسيطة 🚀 #تقنية #برمجة
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 18, color: '#e0e0e0' }}>
          <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" fill="none" strokeWidth="2"><circle cx="9" cy="18" r="3"/><circle cx="20" cy="18" r="1"/><path d="M12 18V6l8-2v11"/></svg>
          tech_world • Original Audio
        </div>
      </div>
    </AbsoluteFill>
  );
};

const { fontFamily } = loadFont();

export const Scene1: React.FC = () => {
  const fps = 30;
  const shot1DurationFrames = Math.round(1.96 * fps);
  const shot2DurationFrames = Math.round((5.86 - 1.96) * fps);

  // Segment 0 contains the words for Scene 1
  const sceneWords = timings.segments[0].words.map((w: any) => ({
    text: w.word.trim(),
    startMs: w.start * 1000,
    endMs: w.end * 1000,
  }));

  const shot1Words = sceneWords.filter(w => w.startMs < 1960);
  const shot2Words = sceneWords.filter(w => w.startMs >= 1960);

  return (
    <AbsoluteFill style={{ backgroundColor: '#050505', color: 'white', fontFamily: 'Alexandria, sans-serif' }}>
      {/* 1) BGM and VO */}
      {/* BGM is continuous, maybe we handle it at Root level, but VO goes here if it's scene-based. Let's assume Scene1 is the whole first 5.86s. We can just place VO here. */}
      
      {/* 2) SFX */}
      <Sequence from={0}>
        <Audio src={staticFile("media/sfx_ui_click_norm.mp3")} volume={1} />
      </Sequence>

      <Series>
        {/* Shot 1: Phone Mockup */}
        <Series.Sequence durationInFrames={shot1DurationFrames}>
          <AbsoluteFill>
            <DeviceMockupZoom device="phone">
              <InstagramReelsUI />
            </DeviceMockupZoom>
          </AbsoluteFill>
          <AbsoluteFill style={{ justifyContent: 'flex-end', paddingBottom: 100 }}>
            <div style={{ direction: 'rtl', flexWrap: 'wrap', willChange: 'transform' }}>
              <Captions
                captions={shot1Words}
                delay={0}
                color="#ffffff"
                accentColor="#4facfe"
                fontSize={60}
                fontFamily={fontFamily}
                fontWeight={800}
                align="center"
              />
            </div>
          </AbsoluteFill>
        </Series.Sequence>

        {/* Shot 2: Moon Video */}
        <Series.Sequence durationInFrames={shot2DurationFrames}>
          <AbsoluteFill>
            <OffthreadVideo 
              src={staticFile("media/pexels_video_12172194_intra.mp4")} 
              style={{ objectFit: 'cover', width: '100%', height: '100%' }}
            />
            {/* Highlight effect over the video to darken it slightly for text */}
            <div style={{ position: 'absolute', inset: 0, backgroundColor: 'rgba(0,0,0,0.4)' }} />
          </AbsoluteFill>
          <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center' }}>
            <Highlight variant="glow" color="#4facfe" delay={Math.round((2.66 - 1.96) * fps)} duration={15} holdFrames={30}>
              <div style={{ padding: '20px 40px', backgroundColor: 'rgba(0,0,0,0.6)', borderRadius: 24, border: '1px solid rgba(255,255,255,0.1)' }}>
                <div style={{ direction: 'rtl', flexWrap: 'wrap', willChange: 'transform' }}>
                  <Captions
                    captions={shot2Words}
                    delay={-(shot1DurationFrames)} 
                    color="#ffffff"
                    accentColor="#4facfe"
                    fontSize={70}
                    fontFamily={fontFamily}
                    fontWeight={800}
                    align="center"
                  />
                </div>
              </div>
            </Highlight>
          </AbsoluteFill>
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
};




