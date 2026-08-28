import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
  staticFile,
  Audio,
  Sequence,
  Video,
} from "remotion";
import { UnifiedCyberBackground } from "./UnifiedCyberBackground";

export const SCENE_6_DURATION_FRAMES = 149; // 28.28s - 33.24s @ 30fps

const TelegramBotScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const scale = spring({ frame, fps, config: { stiffness: 80, damping: 14 } });
  const videoScale = interpolate(frame, [0, 40], [1.2, 1.0]);

  return (
    <AbsoluteFill style={{ background: "black" }}>
      <Video
        src={staticFile("media/pexels_video_telegram.mp4")}
        style={{ width: "100%", height: "100%", objectFit: "cover", opacity: 0.7, transform: `scale(${videoScale})` }}
      />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div style={{
          background: "rgba(20, 10, 40, 0.85)",
          backdropFilter: "blur(25px)",
          WebkitBackdropFilter: "blur(25px)",
          padding: "30px 80px",
          borderRadius: 60,
          border: "3px solid #BD00FF",
          boxShadow: "0 20px 60px rgba(0,0,0,0.5), inset 0 0 30px rgba(189, 0, 255, 0.3)",
          transform: `scale(${scale}) translateY(${interpolate(frame, [0, 20], [50, 0], {extrapolateRight: "clamp"})})`,
          display: "flex",
          alignItems: "center",
          gap: 30
        }}>
          <span style={{ fontSize: 90 }}>🤖</span>
          <span style={{
            fontSize: 80,
            fontWeight: 900,
            color: "#FFFFFF",
            textShadow: "0 0 20px rgba(189, 0, 255, 0.8)",
          }}>بوت تليجرام</span>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const APIScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const scale = spring({ frame, fps, config: { stiffness: 80, damping: 14 } });
  const videoScale = interpolate(frame, [0, 32], [1.2, 1.0]);

  return (
    <AbsoluteFill style={{ background: "black" }}>
      <Video
        src={staticFile("media/pexels_video_api.mp4")}
        style={{ width: "100%", height: "100%", objectFit: "cover", opacity: 0.7, transform: `scale(${videoScale})` }}
      />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div style={{
          background: "rgba(10, 20, 40, 0.85)",
          backdropFilter: "blur(25px)",
          WebkitBackdropFilter: "blur(25px)",
          padding: "30px 80px",
          borderRadius: 60,
          border: "3px solid #00F2FE",
          boxShadow: "0 20px 60px rgba(0,0,0,0.5), inset 0 0 30px rgba(0, 242, 254, 0.3)",
          transform: `scale(${scale}) translateY(${interpolate(frame, [0, 20], [50, 0], {extrapolateRight: "clamp"})})`,
          display: "flex",
          alignItems: "center",
          gap: 30
        }}>
          <span style={{ fontSize: 90 }}>🌐</span>
          <span style={{
            fontSize: 80,
            fontWeight: 900,
            color: "#FFFFFF",
            textShadow: "0 0 20px rgba(0, 242, 254, 0.8)",
          }}>ربط مع APIs</span>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const AutomationScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const videoScale = interpolate(frame, [0, 77], [1.2, 1.0]);
  const dimOpacity = interpolate(frame, [20, 77], [0, 0.7]); // Background dims over time
  
  // "وأنت نايم" starts at 32.34s, which is ~50 frames into this segment.
  const textZoom = interpolate(frame, [50, 77], [0.8, 1.2], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ background: "black" }}>
      <Video
        src={staticFile("media/pexels_video_code.mp4")}
        style={{ width: "100%", height: "100%", objectFit: "cover", opacity: 0.8, transform: `scale(${videoScale})` }}
      />
      <AbsoluteFill style={{ background: "black", opacity: dimOpacity }} />

      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div style={{
          background: "rgba(10, 40, 20, 0.85)",
          backdropFilter: "blur(25px)",
          WebkitBackdropFilter: "blur(25px)",
          padding: "40px 100px",
          borderRadius: 80,
          border: "4px solid #00FFA3",
          boxShadow: "0 30px 80px rgba(0,0,0,0.8), inset 0 0 40px rgba(0, 255, 163, 0.3)",
          transform: `scale(${textZoom}) translateY(${interpolate(frame, [45, 60], [50, 0], {extrapolateRight: "clamp"})})`,
          opacity: interpolate(frame, [45, 55, 70, 77], [0, 1, 1, 0]),
          display: "flex",
          alignItems: "center",
          gap: 40
        }}>
          <span style={{ fontSize: 100 }}>🌙</span>
          <span style={{
            color: "#00FFA3",
            fontSize: 100,
            fontWeight: 950,
            textShadow: "0 0 30px rgba(0, 255, 163, 0.9)",
          }}>وأنت نايم</span>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

export const Scene6Showcase: React.FC<{ includeGlobalAudio?: boolean }> = ({
  includeGlobalAudio = false,
}) => {
  return (
    <AbsoluteFill style={{ overflow: "hidden", fontFamily: "'Alexandria', 'IBM Plex Sans Arabic', sans-serif" }}>
      {/* Global Audio */}
      {includeGlobalAudio && (
        <>
          <Audio src={staticFile("media/vo_audio.wav")} startFrom={849} volume={1.0} />
          <Audio src={staticFile("media/bg_music.wav")} startFrom={849} volume={0.16} />
        </>
      )}

      {/* Sequences for fast-paced showcase */}
      <Sequence from={0} durationInFrames={40}>
        <TelegramBotScene />
      </Sequence>
      
      <Sequence from={40} durationInFrames={32}>
        <APIScene />
      </Sequence>

      <Sequence from={72} durationInFrames={77}>
        <AutomationScene />
      </Sequence>
      
      {/* Sound Effects */}
      <Sequence from={0} durationInFrames={30}>
          <Audio src={staticFile("media/sfx_swoosh.wav")} volume={0.7} />
      </Sequence>
      <Sequence from={54}>
          <Audio src={staticFile("media/sfx_notification.wav")} volume={0.8} />
      </Sequence>
      <Sequence from={72} durationInFrames={30}>
          <Audio src={staticFile("media/sfx_pop.wav")} volume={0.8} />
      </Sequence>
    </AbsoluteFill>
  );
};
