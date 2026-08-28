import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
  staticFile,
  Audio,
  Img,
  Sequence,
} from "remotion";
import { UnifiedCyberBackground } from "./UnifiedCyberBackground";

export const SCENE_1_DURATION_FRAMES = 86; // 0.00s - 2.88s @ 30fps

export const Scene1Hook: React.FC<{ includeGlobalAudio?: boolean }> = ({
  includeGlobalAudio = false,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // -------------------------------------------------------------
  // 1. Single Continuous Smooth Camera Movement
  // -------------------------------------------------------------
  // Smooth pan
  const cameraPanX = interpolate(
    frame,
    [0, 18, 28, 41, 60, 74, 86],
    [30, 15, -15, 0, 0, 0, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Smooth camera scale across the entire scene
  let cameraScale = 1.0;
  if (frame <= 68) {
    cameraScale = interpolate(
      frame,
      [0, 18, 28, 29, 39, 41, 55, 68],
      [1.0, 1.0, 1.10, 1.10, 1.20, 1.20, 1.0, 1.02],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
    );
  } else {
    // Slower, more gradual and cinematic zoom dive (frame 68 to 86)
    const diveProgress = interpolate(frame, [68, 86], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    const smoothEase = Math.pow(diveProgress, 2.3);
    cameraScale = 1.02 + smoothEase * 34.0;
  }

  // Smoothly interpolate transform-origin
  const originX = interpolate(frame, [64, 74], [50, 44], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const originY = interpolate(frame, [64, 74], [50, 82.5], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Smooth fade out of Scene 1 typography at the deepest zoom point
  const scene1FadeOut = interpolate(frame, [82, 86], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Cyan Portal Glow expansion as we dive deep inside the dot
  const portalGlowOpacity = interpolate(frame, [75, 86], [0, 0.9], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // -------------------------------------------------------------
  // 2. Element Animations
  // -------------------------------------------------------------
  const badgeSpring = spring({
    frame,
    fps,
    config: { stiffness: 180, damping: 22 },
  });

  // Text "بثلاثين يوم" fades out smoothly as 30 badge emerges
  const text30Opacity = interpolate(frame, [38, 43], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Giant 30 badge emerges smoothly
  const num30Spring = spring({
    frame: frame - 41,
    fps,
    config: { stiffness: 200, damping: 18 },
  });
  const num30Scale = interpolate(num30Spring, [0, 1], [0.3, 1.0]);
  const num30Opacity = interpolate(frame, [41, 46, 68, 72], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Yellow Neon Circle Draw around "بس؟" (f70 - f77)
  const circleProgress = interpolate(frame, [70, 77], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const circleDashOffset = 380 * (1 - circleProgress);

  return (
    <AbsoluteFill
      style={{
        overflow: "hidden",
        fontFamily: "'Alexandria', 'IBM Plex Sans Arabic', sans-serif",
        textRendering: "geometricPrecision",
      }}
    >
      {/* Standalone Background (Only when previewing Scene 1 alone) */}
      {includeGlobalAudio && <UnifiedCyberBackground />}

      {/* 1. Global Audio Layers (When previewed standalone) */}
      {includeGlobalAudio && (
        <>
          <Audio
            src={staticFile("media/vo_audio.wav")}
            volume={1.0}
          />
          <Audio
            src={staticFile("media/bg_music.wav")}
            volume={0.16}
          />
        </>
      )}

      {/* SFX Tracks with full Sequence representation */}
      <Sequence from={0} durationInFrames={30} name="SFX Whoosh Intro">
        <Audio src={staticFile("media/sfx_whoosh.wav")} volume={0.8} />
      </Sequence>
      <Sequence from={18} durationInFrames={20} name="SFX Pop Tetqen">
        <Audio src={staticFile("media/sfx_pop.wav")} volume={0.8} />
      </Sequence>
      <Sequence from={29} durationInFrames={20} name="SFX Pop Python">
        <Audio src={staticFile("media/sfx_pop.wav")} volume={0.9} />
      </Sequence>
      <Sequence from={41} durationInFrames={35} name="SFX Swoosh 30 Reveal">
        <Audio src={staticFile("media/sfx_swoosh.wav")} volume={0.8} />
      </Sequence>
      <Sequence from={70} durationInFrames={14} name="SFX Digital Question Dive">
        <Audio src={staticFile("media/sfx_swoosh.wav")} volume={0.8} />
      </Sequence>

      {/* Camera Space */}
      <div
        style={{
          position: "relative",
          zIndex: 10,
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "100px 40px",
          boxSizing: "border-box",
          transform: `translateX(${cameraPanX}px) scale(${cameraScale})`,
          transformOrigin: `${originX}% ${originY}%`,
          opacity: scene1FadeOut,
          willChange: "transform",
        }}
      >
        {/* Top Header Badge */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 14,
            padding: "12px 28px",
            borderRadius: 40,
            background: "rgba(10, 20, 38, 0.9)",
            border: "2px solid rgba(0, 229, 255, 0.5)",
            boxShadow:
              "0 0 35px rgba(0, 229, 255, 0.35), inset 0 0 15px rgba(0, 229, 255, 0.2)",
            opacity: badgeSpring,
            transform: `translateY(${interpolate(badgeSpring, [0, 1], [-40, 0])}px)`,
          }}
        >
          <Img
            src={staticFile("media/icon_python.svg")}
            style={{
              width: 44,
              height: 44,
              filter: "drop-shadow(0 0 10px #FFD43B)",
            }}
          />
          <span
            style={{
              fontSize: 28,
              fontWeight: 900,
              color: "#00E5FF",
              letterSpacing: 3,
              textShadow: "0 0 12px rgba(0, 229, 255, 0.6)",
            }}
          >
            PYTHON 30-DAY CHALLENGE
          </span>
        </div>

        {/* Main Center Flow (RTL) */}
        <div
          style={{
            direction: "rtl",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            width: "95%",
            textAlign: "center",
            gap: 25,
            margin: "auto 0",
          }}
        >
          {/* Top Line: بدك تتقن بايثون */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 20,
              flexWrap: "wrap",
            }}
          >
            {/* بدك */}
            <span
              style={{
                fontSize: 74,
                fontWeight: 900,
                color: "#FFFFFF",
                textShadow:
                  frame < 18 ? "0 0 25px rgba(255,255,255,0.9)" : "none",
                transform: `scale(${frame < 18 ? 1.06 : 1.0})`,
                transition: "all 0.15s ease-out",
                display: "inline-block",
                willChange: "transform",
              }}
            >
              بدك
            </span>

            {/* تتقن (Snappy Zoom 1 at f18) */}
            <span
              style={{
                fontSize: 82,
                fontWeight: 900,
                color: frame >= 18 ? "#00FFA3" : "rgba(255,255,255,0.4)",
                textShadow:
                  frame >= 18 && frame < 29
                    ? "0 0 40px #00FFA3, 0 0 18px #00FFA3"
                    : "0 0 10px rgba(0,255,163,0.3)",
                transform: `scale(${frame >= 18 && frame < 29 ? 1.15 : 1.0})`,
                transition: "all 0.15s ease-out",
                padding: "0 6px",
                display: "inline-block",
                willChange: "transform",
              }}
            >
              تتقن
            </span>

            {/* بايثون (Snappy Zoom 2 at f29) */}
            <span
              style={{
                fontSize: 94,
                fontWeight: 950,
                color: frame >= 29 ? "#FFE873" : "rgba(255,255,255,0.4)",
                textShadow:
                  frame >= 29
                    ? "0 0 35px #FFD43B, 0 0 15px #FFE873"
                    : "none",
                transform: `scale(${frame >= 29 && frame < 41 ? 1.18 : 1.0})`,
                transition: "all 0.15s ease-out",
                padding: "0 10px",
                display: "inline-block",
                willChange: "transform",
              }}
            >
              بايثون
            </span>
          </div>

          {/* Middle Fixed Box */}
          <div
            style={{
              height: 250,
              width: "100%",
              position: "relative",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {/* 1. Text "بثلاثين يوم" (f0 - f41) */}
            <div
              style={{
                position: "absolute",
                fontSize: 78,
                fontWeight: 900,
                color: "rgba(255,255,255,0.5)",
                opacity: text30Opacity,
                pointerEvents: "none",
              }}
            >
              بثلاثين يوم
            </div>

            {/* 2. Giant "30" Badge (f41 - f72) */}
            <div
              style={{
                position: "absolute",
                transform: `scale(${num30Scale})`,
                opacity: num30Opacity,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                pointerEvents: "none",
              }}
            >
              <div
                style={{
                  fontSize: 220,
                  fontWeight: 950,
                  lineHeight: 0.85,
                  color: "#FFE600",
                  textShadow:
                    "0 0 50px rgba(255, 200, 0, 0.95), 0 0 20px #FF8800",
                  letterSpacing: -6,
                }}
              >
                30
              </div>

              <div
                style={{
                  marginTop: 10,
                  padding: "8px 34px",
                  borderRadius: 30,
                  background: "linear-gradient(90deg, #FF5500, #FFAA00)",
                  color: "#000000",
                  fontSize: 34,
                  fontWeight: 950,
                  boxShadow: "0 0 35px rgba(255, 85, 0, 0.8)",
                  letterSpacing: 2,
                }}
              >
                يـومـاً فـقـط ⚡
              </div>
            </div>
          </div>

          {/* Bottom Line: بس؟ (with Yellow Neon Oval & Focal Question Mark) */}
          <div
            style={{
              position: "relative",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "14px 40px",
            }}
          >
            {/* Animated Yellow Neon Oval */}
            {frame >= 70 && (
              <svg
                style={{
                  position: "absolute",
                  inset: -14,
                  width: "calc(100% + 28px)",
                  height: "calc(100% + 28px)",
                  pointerEvents: "none",
                  overflow: "visible",
                  filter:
                    "drop-shadow(0 0 20px #FFE600) drop-shadow(0 0 8px #FF8800)",
                }}
                viewBox="0 0 220 110"
              >
                <ellipse
                  cx="110"
                  cy="55"
                  rx="100"
                  ry="46"
                  fill="none"
                  stroke="#FFE600"
                  strokeWidth="6"
                  strokeDasharray="380"
                  strokeDashoffset={circleDashOffset}
                  strokeLinecap="round"
                />
              </svg>
            )}

            <span
              style={{
                fontSize: 88,
                fontWeight: 950,
                color: "#FFE600",
                textShadow: "0 0 25px rgba(255,230,0,0.8)",
                marginLeft: 12,
              }}
            >
              بس
            </span>

            {/* Question Mark: Target Focal Point for Deep Zoom Dive */}
            <span
              style={{
                position: "relative",
                fontSize: 98,
                fontWeight: 950,
                color: "#00E5FF",
                textShadow:
                  "0 0 35px #00E5FF, 0 0 15px #FFFFFF, 0 0 60px #00E5FF",
                display: "inline-block",
                transform: `scale(${frame >= 70 ? 1.2 : 1.0})`,
                transition: "all 0.15s ease-out",
                willChange: "transform",
              }}
            >
              ؟
            </span>
          </div>
        </div>

        {/* Bottom spacer */}
        <div style={{ height: 20 }} />
      </div>

      {/* Layer 4: Cyan Energy Portal Burst (Seamless bridge to Scene 2) */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(circle at 44% 82.5%, rgba(0, 229, 255, 0.85) 0%, rgba(6, 9, 19, 0) 70%)",
          opacity: portalGlowOpacity,
          zIndex: 90,
          pointerEvents: "none",
        }}
      />
    </AbsoluteFill>
  );
};
