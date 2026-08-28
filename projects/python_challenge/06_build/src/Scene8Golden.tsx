import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
  Sequence,
  Audio,
  staticFile,
} from "remotion";

export const SCENE_8_DURATION_FRAMES = 128; // 39.32s - 43.58s = 4.26s @ 30fps

export const Scene8Golden: React.FC<{ includeGlobalAudio?: boolean }> = ({
  includeGlobalAudio = false,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Fast Camera Pan from Right to Left (Simulation)
  const panX = interpolate(frame, [0, 128], [300, -300]);

  // Burst Background (Vibrant Green & Gold) fades in, then fades out at the end
  const bgOpacity = interpolate(
    frame, 
    [0, 10, 115, 128], 
    [0, 1, 1, 0], 
    { extrapolateRight: "clamp" }
  );
  
  // "التطبيق العملي" Animation
  // Hits right away
  const part1Scale = spring({
    frame,
    fps,
    config: { stiffness: 100, damping: 10 },
    from: 0.5,
    to: 1,
  });
  
  const highlighterWidth = spring({
    frame: frame - 5,
    fps,
    config: { stiffness: 50, damping: 15 },
    from: 0,
    to: 100,
  });

  // "مبرمج حقيقي" Animation
  // Starts at frame 86 (42.2s)
  const part2Trigger = frame - 86;
  const part2Scale = spring({
    frame: part2Trigger,
    fps,
    config: { stiffness: 150, damping: 10 },
    from: 0, 
    to: 1,
  });

  // Exit Animation (slides out completely to the left)
  // Starts around frame 115
  const exitTrigger = frame - 115;
  const exitX = spring({
    frame: exitTrigger,
    fps,
    config: { stiffness: 120, damping: 14 },
    from: 0,
    to: -1500, // Slide out completely to the left
  });

  const shieldGlow = interpolate(frame, [86, 100], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ overflow: "hidden", fontFamily: "'Alexandria', sans-serif" }}>
      {/* Global Audio for Standalone */}
      {includeGlobalAudio && (
        <>
          <Audio src={staticFile("media/vo_audio.wav")} startFrom={1180} volume={1.0} />
          <Audio src={staticFile("media/bg_music.wav")} startFrom={1180} volume={0.16} />
        </>
      )}

      {/* Vibrant Background */}
      <AbsoluteFill
        style={{
          background: "radial-gradient(circle at center, #0B193D 0%, #000000 100%)", // Changed to Deep Blue
          opacity: bgOpacity,
        }}
      >
        {/* Dynamic Light Rays */}
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            width: "200%",
            height: "200%",
            transform: `translate(-50%, -50%) rotate(${frame * 0.5}deg)`,
            background: "conic-gradient(from 0deg, transparent 0deg, rgba(0, 242, 254, 0.1) 45deg, transparent 90deg, rgba(255, 230, 0, 0.1) 135deg, transparent 180deg, rgba(0, 242, 254, 0.1) 225deg, transparent 270deg, rgba(255, 230, 0, 0.1) 315deg, transparent 360deg)",
          }}
        />
      </AbsoluteFill>

      {/* Camera Container */}
      <AbsoluteFill style={{ transform: `translateX(${panX}px)`, alignItems: "center", justifyContent: "center" }}>
        
        {/* Sequence 1: التطبيق العملي اليومي */}
        <Sequence from={0} durationInFrames={86}>
          <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
            <div style={{ transform: `scale(${part1Scale})`, display: "flex", flexDirection: "column", alignItems: "center", gap: 30 }}>
              
              <div style={{ position: "relative", padding: "10px 30px" }}>
                {/* Highlighter Background */}
                <div
                  style={{
                    position: "absolute",
                    top: 0,
                    right: 0,
                    height: "100%",
                    width: `${highlighterWidth}%`,
                    backgroundColor: "#00F2FE", // Cyan Highlighter
                    zIndex: -1,
                    transform: "skewX(-10deg)",
                    boxShadow: "0 0 30px rgba(0, 242, 254, 0.6)",
                  }}
                />
                <h1 style={{ color: "#000", fontSize: 110, fontWeight: 950, margin: 0, textShadow: "0px 4px 10px rgba(0,0,0,0.2)" }}>
                  التطبيق العملي
                </h1>
              </div>

              <h2 style={{ color: "white", fontSize: 70, margin: 0, opacity: interpolate(frame, [15, 25], [0, 1]) }}>
                اليومي
              </h2>
            </div>
          </AbsoluteFill>
        </Sequence>

        {/* Sequence 2: مبرمج حقيقي */}
        <Sequence from={86} durationInFrames={128 - 86}>
          <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
            <div
              style={{
                transform: `translateX(${exitX}px) scale(${part2Scale})`,
                padding: "60px 100px",
                border: "6px solid #FFE600",
                borderRadius: 40,
                position: "relative",
                boxShadow: `0 0 ${shieldGlow * 80}px rgba(255, 230, 0, 0.8), inset 0 0 ${shieldGlow * 40}px rgba(255, 230, 0, 0.4)`,
                background: "rgba(20, 20, 0, 0.8)",
                backdropFilter: "blur(20px)",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 20
              }}
            >
              {/* Shield Icon */}
              <div
                style={{
                  position: "absolute",
                  top: -60,
                  fontSize: 100,
                  filter: `drop-shadow(0 0 30px rgba(255, 230, 0, 1))`,
                  transform: `translateY(${Math.sin(frame / 5) * 10}px)`
                }}
              >
                🛡️
              </div>
              
              <h1
                style={{
                  color: "#FFE600",
                  fontSize: 120,
                  fontWeight: 950,
                  margin: 0,
                  textShadow: "0 10px 40px rgba(255, 230, 0, 0.6)",
                  textAlign: "center",
                }}
              >
                مبرمج
                <br />
                حقيقي
              </h1>
            </div>
          </AbsoluteFill>
        </Sequence>

      </AbsoluteFill>
      
      {/* Sound Effects */}
      <Sequence from={0}>
        <Audio src={staticFile("media/sfx_swoosh.wav")} volume={0.8} />
      </Sequence>
      <Sequence from={86}>
        <Audio src={staticFile("media/sfx_swish_metal.wav")} volume={0.6} />
      </Sequence>

    </AbsoluteFill>
  );
};
