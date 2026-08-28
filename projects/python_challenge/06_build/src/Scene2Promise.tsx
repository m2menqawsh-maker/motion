import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
  staticFile,
  Audio,
  Video,
  Img,
  Sequence,
} from "remotion";
import { UnifiedCyberBackground } from "./UnifiedCyberBackground";

export const SCENE_2_DURATION_FRAMES = 137; // 2.88s - 7.44s @ 30fps

export const Scene2Promise: React.FC<{ includeGlobalAudio?: boolean }> = ({
  includeGlobalAudio = false,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // -------------------------------------------------------------
  // 1. Dynamic Active Camera Movement (Tracks spatial text locations)
  // -------------------------------------------------------------
  // Camera Pan X: shifts to track text across different sides of the screen
  const cameraPanX = interpolate(
    frame,
    [0, 15, 24, 45, 54, 75, 84, 110],
    [-25, -25, 40, 40, -65, -65, 0, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Camera Pan Y: tracks vertical story progression
  const cameraPanY = interpolate(
    frame,
    [0, 15, 24, 45, 54, 75, 84, 110],
    [40, 40, -35, -35, -15, -15, 0, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Camera Scale: dynamic zooms on key moments
  const cameraScale = interpolate(
    frame,
    [0, 15, 24, 45, 54, 75, 84, 110],
    [1.12, 1.12, 1.08, 1.08, 1.20, 1.20, 1.0, 1.0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // -------------------------------------------------------------
  // 2. Spatial Elements Animations & Springs
  // -------------------------------------------------------------
  // Overall Scene Smooth Fade In (f0 - f12)
  const sceneFadeIn = interpolate(frame, [0, 12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Square Window Entrance (f0 - f20)
  const windowEntrance = spring({
    frame,
    fps,
    config: { stiffness: 120, damping: 20 },
  });
  const windowScale = interpolate(windowEntrance, [0, 1], [0.75, 1.0]);

  // Location 1: "من الصفر" (Top-Right / Top Area, f0 - f30)
  const step1Spring = spring({
    frame: frame - 2,
    fps,
    config: { stiffness: 140, damping: 20 },
  });
  const step1Y = interpolate(step1Spring, [0, 1], [-30, 0]);
  const step1Opacity = interpolate(frame, [0, 8, 48, 54], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Location 2: "لآخر سكربت" (Bottom-Left Area, f22 - f54)
  const scriptSpring = spring({
    frame: frame - 22,
    fps,
    config: { stiffness: 140, damping: 18 },
  });
  const scriptX = interpolate(scriptSpring, [0, 1], [-40, 0]);
  const scriptScale = interpolate(scriptSpring, [0, 1], [0.8, 1.0]);
  const scriptOpacity = interpolate(frame, [22, 30, 48, 54], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Location 3: "ذكاء اصطناعي" (Right Side Hologram Box, f54 - f84)
  const windowShiftSpring = spring({
    frame: frame - 52,
    fps,
    config: { stiffness: 160, damping: 20 },
  });
  const windowShiftX = interpolate(windowShiftSpring, [0, 1], [0, -170]);
  const windowShiftScale = interpolate(windowShiftSpring, [0, 1], [1.0, 0.82]);

  const aiBoxSpring = spring({
    frame: frame - 55,
    fps,
    config: { stiffness: 160, damping: 18 },
  });
  const aiBoxX = interpolate(aiBoxSpring, [0, 1], [60, 0]);
  const aiBoxScale = interpolate(aiBoxSpring, [0, 1], [0.75, 1.0]);
  const aiBoxOpacity = interpolate(frame, [54, 62, 80, 85], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Location 4: "بتبرمجه بإيدك!" (Bottom Center Climax, f84 - f137)
  const byHandSpring = spring({
    frame: frame - 84,
    fps,
    config: { stiffness: 160, damping: 20 },
  });
  const byHandY = interpolate(byHandSpring, [0, 1], [35, 0]);
  const byHandOpacity = interpolate(frame, [84, 92], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Hand-drawn Neon Yellow Marker Underline (f89 - f105)
  const markerProgress = interpolate(frame, [89, 105], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const markerDashOffset = 340 * (1 - markerProgress);

  // Transition out to Scene 3 (f122 - f137)
  const exitSlide = interpolate(frame, [122, 137], [0, -1080], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        overflow: "hidden",
        fontFamily: "'Alexandria', 'IBM Plex Sans Arabic', sans-serif",
        transform: `translateX(${exitSlide}px)`,
        opacity: sceneFadeIn,
      }}
    >
      {/* Standalone Background */}
      {includeGlobalAudio && <UnifiedCyberBackground />}

      {/* Global Audio */}
      {includeGlobalAudio && (
        <>
          <Audio
            src={staticFile("media/vo_audio.wav")}
            startFrom={86}
            volume={1.0}
          />
          <Audio
            src={staticFile("media/bg_music.wav")}
            startFrom={86}
            volume={0.16}
          />
        </>
      )}

      {/* SFX Tracks */}
      <Sequence from={0} durationInFrames={30} name="SFX Swoosh In">
        <Audio src={staticFile("media/sfx_swoosh.wav")} volume={0.8} />
      </Sequence>
      <Sequence from={0} durationInFrames={60} name="SFX Keyboard Typing">
        <Audio src={staticFile("media/sfx_keyboard.wav")} volume={0.6} />
      </Sequence>
      <Sequence from={54} durationInFrames={30} name="SFX AI Pop">
        <Audio src={staticFile("media/sfx_pop.wav")} volume={1.0} />
      </Sequence>
      <Sequence from={88} durationInFrames={30} name="SFX Marker Draw">
        <Audio src={staticFile("media/sfx_digital.wav")} volume={0.8} />
      </Sequence>

      {/* Dynamic Camera Tracking Stage */}
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
          padding: "80px 40px",
          boxSizing: "border-box",
          transform: `translate(${cameraPanX}px, ${cameraPanY}px) scale(${cameraScale})`,
          transformOrigin: "50% 50%",
        }}
      >
        {/* Top Header Pill */}
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 10,
            padding: "8px 24px",
            borderRadius: 30,
            background: "rgba(10, 20, 42, 0.9)",
            border: "1.5px solid rgba(0, 229, 255, 0.5)",
            boxShadow: "0 0 25px rgba(0, 229, 255, 0.3)",
          }}
        >
          <span style={{ fontSize: 20 }}>🚀</span>
          <span
            style={{
              fontSize: 22,
              fontWeight: 800,
              color: "#00E5FF",
              letterSpacing: 2,
            }}
          >
            ROADMAP • رحلة الـ 30 يوماً
          </span>
        </div>

        {/* Center Arena: Window & Spatial Multi-Location Text Elements */}
        <div
          style={{
            position: "relative",
            width: "100%",
            maxWidth: 980,
            height: 800,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {/* ========================================================= */}
          {/* LOCATION 1: "مِـن الـصـفـر" (Top-Right of Window Area) */}
          {/* ========================================================= */}
          {frame < 54 && (
            <div
              style={{
                position: "absolute",
                top: 30,
                right: 30,
                direction: "rtl",
                display: "flex",
                alignItems: "center",
                gap: 12,
                padding: "10px 28px",
                borderRadius: 20,
                background: "rgba(6, 18, 38, 0.92)",
                border: "2px solid #00F2FE",
                boxShadow: "0 0 35px rgba(0, 242, 254, 0.5)",
                transform: `translateY(${step1Y}px)`,
                opacity: step1Opacity,
                zIndex: 25,
              }}
            >
              <div
                style={{
                  width: 14,
                  height: 14,
                  borderRadius: "50%",
                  backgroundColor: "#00F2FE",
                  boxShadow: "0 0 12px #00F2FE",
                }}
              />
              <span
                style={{
                  fontSize: 48,
                  fontWeight: 900,
                  color: "#00F2FE",
                  letterSpacing: 1,
                  textShadow: "0 0 20px #00F2FE",
                }}
              >
                مِـن الـصـفـر
              </span>
            </div>
          )}

          {/* ========================================================= */}
          {/* CENTER WINDOW: Square Framed Window (Coding Video) */}
          {/* ========================================================= */}
          <div
            style={{
              position: "absolute",
              width: 580,
              height: 580,
              borderRadius: 28,
              overflow: "hidden",
              border: "3px solid #00F2FE",
              boxShadow:
                "0 0 50px rgba(0, 242, 254, 0.45), 0 0 90px rgba(168, 85, 247, 0.22)",
              background: "#080E1D",
              transform: `translateX(${windowShiftX}px) scale(${windowScale * windowShiftScale})`,
              display: "flex",
              flexDirection: "column",
              zIndex: 15,
            }}
          >
            {/* Window Header Bar */}
            <div
              style={{
                height: 44,
                backgroundColor: "rgba(8, 14, 29, 0.95)",
                borderBottom: "1px solid rgba(0, 242, 254, 0.3)",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "0 18px",
                boxSizing: "border-box",
              }}
            >
              {/* Traffic dots */}
              <div style={{ display: "flex", gap: 8 }}>
                <div
                  style={{
                    width: 12,
                    height: 12,
                    borderRadius: "50%",
                    backgroundColor: "#FF5F56",
                  }}
                />
                <div
                  style={{
                    width: 12,
                    height: 12,
                    borderRadius: "50%",
                    backgroundColor: "#FFBD2E",
                  }}
                />
                <div
                  style={{
                    width: 12,
                    height: 12,
                    borderRadius: "50%",
                    backgroundColor: "#27C93F",
                  }}
                />
              </div>

              {/* Window Title */}
              <span
                style={{
                  color: "#00F2FE",
                  fontSize: 16,
                  fontWeight: 800,
                  fontFamily: "'JetBrains Mono', monospace",
                  letterSpacing: 1,
                }}
              >
                ⚡ python_core.py
              </span>

              {/* Status */}
              <span
                style={{
                  color: "#27C93F",
                  fontSize: 13,
                  fontWeight: 900,
                  fontFamily: "'JetBrains Mono', monospace",
                }}
              >
                ● ACTIVE
              </span>
            </div>

            {/* Video Body */}
            <div
              style={{
                position: "relative",
                width: "100%",
                flex: 1,
                overflow: "hidden",
              }}
            >
              <Video
                src={staticFile("media/video_coding_keyboard.mp4")}
                style={{
                  width: "100%",
                  height: "100%",
                  objectFit: "cover",
                }}
                playbackRate={1.3}
                muted
              />

              {/* Cyber Grid */}
              <div
                style={{
                  position: "absolute",
                  inset: 0,
                  background:
                    "linear-gradient(rgba(0, 229, 255, 0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 229, 255, 0.08) 1px, transparent 1px)",
                  backgroundSize: "28px 28px",
                  pointerEvents: "none",
                }}
              />
            </div>
          </div>

          {/* ========================================================= */}
          {/* LOCATION 2: "لآخِـر سـكـربـت" (Bottom-Left of Window) */}
          {/* ========================================================= */}
          {frame >= 20 && frame < 54 && (
            <div
              style={{
                position: "absolute",
                bottom: 40,
                left: 40,
                direction: "rtl",
                display: "flex",
                alignItems: "center",
                gap: 12,
                padding: "12px 30px",
                borderRadius: 22,
                background: "rgba(28, 20, 6, 0.94)",
                border: "2px solid #FFD700",
                boxShadow: "0 0 35px rgba(255, 215, 0, 0.5)",
                transform: `translateX(${scriptX}px) scale(${scriptScale})`,
                opacity: scriptOpacity,
                zIndex: 25,
              }}
            >
              <span style={{ fontSize: 32 }}>⚡</span>
              <span
                style={{
                  fontSize: 48,
                  fontWeight: 900,
                  color: "#FFE24A",
                  letterSpacing: 1,
                  textShadow: "0 0 20px rgba(255, 215, 0, 0.8)",
                }}
              >
                لآخِـر سـكـربـت
              </span>
            </div>
          )}

          {/* ========================================================= */}
          {/* LOCATION 3: "ذكـاء اصـطـنـاعـي" (Right Side Hologram Card) */}
          {/* ========================================================= */}
          {frame >= 52 && frame < 86 && (
            <div
              style={{
                position: "absolute",
                right: 20,
                width: 440,
                borderRadius: 26,
                background: "rgba(0, 229, 255, 0.16)",
                border: "2.5px solid #00F2FE",
                boxShadow:
                  "0 0 50px rgba(0, 242, 254, 0.7), inset 0 0 25px rgba(0, 242, 254, 0.3)",
                padding: "26px 24px",
                boxSizing: "border-box",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                gap: 14,
                transform: `translateX(${aiBoxX}px) scale(${aiBoxScale})`,
                opacity: aiBoxOpacity,
                zIndex: 25,
                backdropFilter: "blur(12px)",
              }}
            >
              {/* Bot Icon Badge */}
              <div
                style={{
                  width: 70,
                  height: 70,
                  borderRadius: 18,
                  background: "rgba(0, 242, 254, 0.22)",
                  border: "2px solid #00F2FE",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: "0 0 25px rgba(0, 242, 254, 0.6)",
                }}
              >
                <Img
                  src={staticFile("media/icon_bot.svg")}
                  style={{ width: 44, height: 44 }}
                />
              </div>

              {/* Title */}
              <div
                style={{
                  direction: "rtl",
                  fontSize: 44,
                  fontWeight: 900,
                  color: "#FFFFFF",
                  textShadow:
                    "0 0 30px #00F2FE, 0 0 15px #00F2FE, 0 0 50px #00F2FE",
                  textAlign: "center",
                  lineHeight: 1.25,
                }}
              >
                ذكـاء اصـطـنـاعـي
              </div>

              {/* Sub-pill */}
              <div
                style={{
                  padding: "5px 16px",
                  borderRadius: 20,
                  background: "#00F2FE",
                  color: "#05121F",
                  fontSize: 16,
                  fontWeight: 900,
                  fontFamily: "'JetBrains Mono', monospace",
                  letterSpacing: 1,
                  boxShadow: "0 0 20px #00F2FE",
                }}
              >
                AI MODEL PIPELINE
              </div>
            </div>
          )}
        </div>

        {/* ========================================================= */}
        {/* LOCATION 4: "بتبرمجه بإيدك!" (Bottom Center Climax with Marker) */}
        {/* ========================================================= */}
        <div
          style={{
            direction: "rtl",
            width: "100%",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            transform: `translateY(${byHandY}px)`,
            opacity: byHandOpacity,
            minHeight: 100,
          }}
        >
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 16,
              fontSize: 64,
              fontWeight: 950,
              color: "#FFFFFF",
              textShadow: "0 0 25px rgba(255,255,255,0.7)",
            }}
          >
            <span>بِـتـبـرمـجـه</span>

            {/* Word "بإيدك!" with hand-drawn marker underline */}
            <div
              style={{
                position: "relative",
                display: "inline-block",
                color: "#FFE600",
                textShadow:
                  "0 0 35px #FFE600, 0 0 15px #FFD700, 0 0 60px #FF8800",
              }}
            >
              <span>بـإيـدك!</span>

              {/* Hand-drawn Neon Yellow Marker Underline */}
              {frame >= 88 && (
                <svg
                  style={{
                    position: "absolute",
                    bottom: -22,
                    right: -10,
                    width: "calc(100% + 20px)",
                    height: 32,
                    pointerEvents: "none",
                    overflow: "visible",
                    filter:
                      "drop-shadow(0 0 16px #FFE600) drop-shadow(0 0 6px #FF8800)",
                  }}
                  viewBox="0 0 260 40"
                  fill="none"
                >
                  <path
                    d="M 5,28 Q 70,8 140,24 T 255,16"
                    stroke="#FFE600"
                    strokeWidth="9"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeDasharray="340"
                    strokeDashoffset={markerDashOffset}
                  />
                  <path
                    d="M 15,34 Q 90,16 170,30 T 250,22"
                    stroke="#FF8800"
                    strokeWidth="5"
                    strokeLinecap="round"
                    strokeDasharray="340"
                    strokeDashoffset={markerDashOffset}
                    opacity={0.8}
                  />
                </svg>
              )}
            </div>

            <span style={{ fontSize: 58 }}>✍️</span>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
