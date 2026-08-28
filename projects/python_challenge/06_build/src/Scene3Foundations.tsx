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

export const SCENE_3_DURATION_FRAMES = 242; // 7.44s - 15.50s @ 30fps

export const Scene3Foundations: React.FC<{ includeGlobalAudio?: boolean }> = ({
  includeGlobalAudio = false,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // -------------------------------------------------------------
  // 1. Dynamic Camera Movement
  // -------------------------------------------------------------
  const cameraScale = interpolate(
    frame,
    [0, 30, 75, 95, 125, 135, 155, 165, 185, 196, 242],
    [1.0, 1.0, 1.0, 1.15, 1.15, 1.15, 1.15, 1.15, 1.15, 1.0, 1.0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const cameraPanY = interpolate(
    frame,
    [0, 40, 75, 95, 185, 196],
    [0, 0, 0, -10, -10, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // -------------------------------------------------------------
  // 2. Rolling Counter (1 -> 10)
  // -------------------------------------------------------------
  const counterValue = Math.min(
    10,
    Math.max(
      1,
      Math.floor(
        interpolate(frame, [4, 34], [1, 10], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        })
      )
    )
  );

  // -------------------------------------------------------------
  // 3. Hero Intro (f0 - f80): Centered Hero Block that ascends to Top
  // -------------------------------------------------------------
  const heroEntrance = spring({
    frame,
    fps,
    config: { stiffness: 120, damping: 20 },
  });
  const heroScale = interpolate(heroEntrance, [0, 1], [0.8, 1.0]);

  // Transition from Center Hero to Top Header at f72 - f85
  const heroAscendProgress = interpolate(frame, [72, 85], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const heroY = interpolate(heroAscendProgress, [0, 1], [0, -680]);
  const heroScaleAscend = interpolate(heroAscendProgress, [0, 1], [1.0, 0.88]);

  // -------------------------------------------------------------
  // 4. Sequential Solo Square Card Transitions (f80 - f184)
  // -------------------------------------------------------------
  // Solo Card 1 (متغيرات): enters at f80, slides out to left at f123
  const card1SoloSpring = spring({
    frame: frame - 80,
    fps,
    config: { stiffness: 150, damping: 18 },
  });
  const card1SoloX = interpolate(
    frame,
    [80, 92, 122, 128],
    [400, 0, 0, -800],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const card1SoloOpacity = interpolate(
    frame,
    [80, 88, 122, 128],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Solo Card 2 (لوبات): enters from right at f124, slides out to left at f153
  const card2SoloSpring = spring({
    frame: frame - 124,
    fps,
    config: { stiffness: 150, damping: 18 },
  });
  const card2SoloX = interpolate(
    frame,
    [124, 134, 152, 158],
    [800, 0, 0, -800],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const card2SoloOpacity = interpolate(
    frame,
    [124, 132, 152, 158],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Solo Card 3 (آلة حاسبة): enters from right at f154, transitions into grid at f185
  const card3SoloSpring = spring({
    frame: frame - 154,
    fps,
    config: { stiffness: 150, damping: 18 },
  });
  const card3SoloX = interpolate(
    frame,
    [154, 164, 184, 188],
    [800, 0, 0, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const card3SoloOpacity = interpolate(
    frame,
    [154, 162, 184, 188],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // -------------------------------------------------------------
  // 5. Grand Zoom-Out 3 Square Cards Showcase (f184 - f242)
  // -------------------------------------------------------------
  const allCardsSpring = spring({
    frame: frame - 184,
    fps,
    config: { stiffness: 140, damping: 18 },
  });
  const allCardsScale = interpolate(allCardsSpring, [0, 1], [0.8, 1.0]);
  const allCardsOpacity = interpolate(frame, [184, 190], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Staggered pop for cards 1, 2, 3 in final state
  const c1FinalSpring = spring({ frame: frame - 185, fps, config: { stiffness: 180, damping: 16 } });
  const c2FinalSpring = spring({ frame: frame - 188, fps, config: { stiffness: 180, damping: 16 } });
  const c3FinalSpring = spring({ frame: frame - 191, fps, config: { stiffness: 180, damping: 16 } });

  // Banner Spring (f185+)
  const bannerSpring = spring({
    frame: frame - 185,
    fps,
    config: { stiffness: 200, damping: 16 },
  });
  const bannerScale = interpolate(bannerSpring, [0, 1], [0.6, 1.0]);

  // Exit transition to Scene 4 (f228 - f242)
  const exitSlide = interpolate(frame, [228, 242], [0, -1080], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        overflow: "hidden",
        fontFamily: "'Alexandria', 'IBM Plex Sans Arabic', sans-serif",
        transform: `translateX(${exitSlide}px)`,
      }}
    >
      {/* Standalone Background */}
      {includeGlobalAudio && <UnifiedCyberBackground />}

      {/* Global Audio */}
      {includeGlobalAudio && (
        <>
          <Audio
            src={staticFile("media/vo_audio.wav")}
            startFrom={223}
            volume={1.0}
          />
          <Audio
            src={staticFile("media/bg_music.wav")}
            startFrom={223}
            volume={0.16}
          />
        </>
      )}

      {/* SFX Tracks */}
      <Sequence from={54} durationInFrames={40} name="SFX Database Card">
        <Audio src={staticFile("media/sfx_pop.wav")} volume={0.7} />
      </Sequence>
      <Sequence from={80} durationInFrames={30} name="SFX Card 1 Solo Zoom">
        <Audio src={staticFile("media/sfx_pop.wav")} volume={1.0} />
      </Sequence>
      <Sequence from={124} durationInFrames={30} name="SFX Card 2 Transition">
        <Audio src={staticFile("media/sfx_swoosh.wav")} volume={0.9} />
      </Sequence>
      <Sequence from={154} durationInFrames={30} name="SFX Card 3 Transition">
        <Audio src={staticFile("media/sfx_swoosh.wav")} volume={0.9} />
      </Sequence>
      <Sequence from={185} durationInFrames={35} name="SFX Zoom Out">
        <Audio src={staticFile("media/sfx_notification.wav")} volume={1.0} />
      </Sequence>

      {/* Main Camera Canvas Space */}
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
          padding: "60px 35px",
          boxSizing: "border-box",
          transform: `translateY(${cameraPanY}px) scale(${cameraScale})`,
          transformOrigin: "50% 50%",
        }}
      >
        {/* ========================================================= */}
        {/* HERO INTRO BLOCK (Prominent Big Header) */}
        {/* ========================================================= */}
        <div
          style={{
            position: "absolute",
            top: "50%",
            transform: `translateY(calc(-50% + ${heroY}px)) scale(${heroScale * heroScaleAscend})`,
            zIndex: 30,
            direction: "rtl",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 20,
            width: "100%",
            textAlign: "center",
            transition: "all 0.1s linear",
          }}
        >
          {/* Phase 1 Pill (Big & Prominent) */}
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 16,
              padding: "16px 48px",
              borderRadius: 40,
              background: "rgba(8, 16, 36, 0.96)",
              border: "3px solid #00F2FE",
              boxShadow: "0 0 50px rgba(0, 242, 254, 0.65)",
            }}
          >
            <span style={{ fontSize: 36 }}>🧱</span>
            <span
              style={{
                fontSize: 34,
                fontWeight: 950,
                color: "#00E5FF",
                letterSpacing: 2,
                textShadow: "0 0 25px #00E5FF",
              }}
            >
              المرحلة الأولى • مسار الأساسيات
            </span>
          </div>

          {/* Giant Rolling Counter Showcase (f0 - f75) */}
          {heroAscendProgress < 0.6 && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 20,
                margin: "16px 0",
              }}
            >
              <span
                style={{
                  fontSize: 170,
                  fontWeight: 950,
                  color: "#FFE600",
                  textShadow:
                    "0 0 60px rgba(255, 230, 0, 0.95), 0 0 25px #FF8800",
                  lineHeight: 1,
                }}
              >
                {counterValue}
              </span>
              <span
                style={{
                  fontSize: 78,
                  fontWeight: 950,
                  color: "#FFFFFF",
                  textShadow: "0 0 35px rgba(255,255,255,0.8)",
                }}
              >
                أيـــام ⚡
              </span>
            </div>
          )}

          {/* Heading (Large & High Contrast) */}
          <div
            style={{
              fontSize: heroAscendProgress < 0.6 ? 68 : 58,
              fontWeight: 950,
              color: "#FFFFFF",
              textShadow: "0 0 35px rgba(255,255,255,0.7)",
            }}
          >
            بتتعلم{" "}
            <span
              style={{
                color: "#00FFA3",
                textShadow: "0 0 45px #00FFA3, 0 0 20px #00FFA3",
              }}
            >
              الأساسيات البرمجية
            </span>
          </div>
        </div>

        {/* ========================================================= */}
        {/* CENTER ARENA: Solo Square Cards (f80 - f184) & 3 Square Cards (f184+) */}
        {/* ========================================================= */}
        <div
          style={{
            position: "relative",
            width: "100%",
            maxWidth: 1000,
            flex: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            marginTop: 140,
            marginBottom: 20,
          }}
        >
          {/* ========================================================= */}
          {/* SOLO SQUARE CARD 1: [متغيرات x = 10] (f80 - f125) */}
          {/* Layout: Top Pill -> Center Badge -> Title & Code */}
          {/* ========================================================= */}
          {frame >= 78 && frame < 130 && (
            <div
              style={{
                position: "absolute",
                width: 620,
                height: 620,
                borderRadius: 36,
                background: "rgba(10, 18, 36, 0.98)",
                border: "3.5px solid #00F2FE",
                boxShadow:
                  "0 0 70px rgba(0, 242, 254, 0.6), inset 0 0 30px rgba(0, 242, 254, 0.2)",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "36px 30px 40px 30px",
                boxSizing: "border-box",
                direction: "rtl",
                textAlign: "center",
                transform: `translateX(${card1SoloX}px) scale(${card1SoloSpring})`,
                opacity: card1SoloOpacity,
                zIndex: 20,
              }}
            >
              {/* 1. Top Pill */}
              <div
                style={{
                  padding: "10px 30px",
                  borderRadius: 24,
                  background: "rgba(0, 242, 254, 0.18)",
                  border: "2px solid #00F2FE",
                  color: "#FFFFFF",
                  fontSize: 22,
                  fontWeight: 900,
                  fontFamily: "'JetBrains Mono', monospace",
                  letterSpacing: 2,
                  boxShadow: "0 0 20px rgba(0, 242, 254, 0.4)",
                }}
              >
                DAY 01 • VARIABLES
              </div>

              {/* 2. Center Square Code Badge */}
              <div
                style={{
                  width: 170,
                  height: 170,
                  borderRadius: 28,
                  background: "rgba(0, 242, 254, 0.2)",
                  border: "3px solid #00F2FE",
                  boxShadow: "0 0 35px rgba(0, 242, 254, 0.7)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#00F2FE",
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 52,
                  fontWeight: 950,
                }}
              >
                x = 10
              </div>

              {/* 3. Bottom Title & Code */}
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 14, width: "100%" }}>
                <div
                  style={{
                    fontSize: 46,
                    fontWeight: 950,
                    color: "#FFFFFF",
                    textShadow: "0 0 25px rgba(255,255,255,0.7)",
                  }}
                >
                  المتغيرات والبيانات
                </div>
                <div
                  style={{
                    padding: "8px 24px",
                    borderRadius: 14,
                    background: "rgba(0, 0, 0, 0.85)",
                    border: "1.5px solid rgba(0, 242, 254, 0.4)",
                    color: "#79C0FF",
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 22,
                    fontWeight: 800,
                  }}
                >
                  name = "Python" • count = 10
                </div>
              </div>
            </div>
          )}

          {/* ========================================================= */}
          {/* SOLO SQUARE CARD 2: [لوبات for loop] (f124 - f155) */}
          {/* Layout: Top Pill -> Center Badge -> Title & Code */}
          {/* ========================================================= */}
          {frame >= 122 && frame < 160 && (
            <div
              style={{
                position: "absolute",
                width: 620,
                height: 620,
                borderRadius: 36,
                background: "rgba(8, 28, 20, 0.98)",
                border: "3.5px solid #00FFA3",
                boxShadow:
                  "0 0 70px rgba(0, 255, 163, 0.6), inset 0 0 30px rgba(0, 255, 163, 0.2)",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "36px 30px 40px 30px",
                boxSizing: "border-box",
                direction: "rtl",
                textAlign: "center",
                transform: `translateX(${card2SoloX}px) scale(${card2SoloSpring})`,
                opacity: card2SoloOpacity,
                zIndex: 20,
              }}
            >
              {/* 1. Top Pill */}
              <div
                style={{
                  padding: "10px 30px",
                  borderRadius: 24,
                  background: "rgba(0, 255, 163, 0.18)",
                  border: "2px solid #00FFA3",
                  color: "#FFFFFF",
                  fontSize: 22,
                  fontWeight: 900,
                  fontFamily: "'JetBrains Mono', monospace",
                  letterSpacing: 2,
                  boxShadow: "0 0 20px rgba(0, 255, 163, 0.4)",
                }}
              >
                DAY 05 • FOR LOOPS
              </div>

              {/* 2. Center Spinning Repeat Icon Badge */}
              <div
                style={{
                  width: 170,
                  height: 170,
                  borderRadius: 28,
                  background: "rgba(0, 255, 163, 0.2)",
                  border: "3px solid #00FFA3",
                  boxShadow: "0 0 35px rgba(0, 255, 163, 0.7)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Img
                  src={staticFile("media/icon_repeat.svg")}
                  style={{
                    width: 100,
                    height: 100,
                    transform: `rotate(${frame * 3}deg)`,
                  }}
                />
              </div>

              {/* 3. Bottom Title & Code */}
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 14, width: "100%" }}>
                <div
                  style={{
                    fontSize: 46,
                    fontWeight: 950,
                    color: "#FFFFFF",
                    textShadow: "0 0 25px rgba(255,255,255,0.7)",
                  }}
                >
                  اللوبات والتكرار الذكي
                </div>
                <div
                  style={{
                    padding: "8px 24px",
                    borderRadius: 14,
                    background: "rgba(0, 0, 0, 0.85)",
                    border: "1.5px solid rgba(0, 255, 163, 0.4)",
                    color: "#56D364",
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 22,
                    fontWeight: 800,
                  }}
                >
                  for day in range(1, 11):
                </div>
              </div>
            </div>
          )}

          {/* ========================================================= */}
          {/* SOLO SQUARE CARD 3: [آلة حاسبة Calculator] (f154 - f185) */}
          {/* Layout: Top Pill -> Center Badge -> Title & Code */}
          {/* ========================================================= */}
          {frame >= 152 && frame < 188 && (
            <div
              style={{
                position: "absolute",
                width: 620,
                height: 620,
                borderRadius: 36,
                background: "rgba(34, 20, 6, 0.98)",
                border: "3.5px solid #FF9500",
                boxShadow:
                  "0 0 70px rgba(255, 149, 0, 0.65), inset 0 0 30px rgba(255, 149, 0, 0.2)",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "36px 30px 40px 30px",
                boxSizing: "border-box",
                direction: "rtl",
                textAlign: "center",
                transform: `translateX(${card3SoloX}px) scale(${card3SoloSpring})`,
                opacity: card3SoloOpacity,
                zIndex: 20,
              }}
            >
              {/* 1. Top Pill */}
              <div
                style={{
                  padding: "10px 30px",
                  borderRadius: 24,
                  background: "rgba(255, 149, 0, 0.2)",
                  border: "2px solid #FF9500",
                  color: "#FFFFFF",
                  fontSize: 22,
                  fontWeight: 900,
                  fontFamily: "'JetBrains Mono', monospace",
                  letterSpacing: 2,
                  boxShadow: "0 0 20px rgba(255, 149, 0, 0.4)",
                }}
              >
                DAY 10 • FIRST PROJECT
              </div>

              {/* 2. Center Calculator Icon Badge */}
              <div
                style={{
                  width: 170,
                  height: 170,
                  borderRadius: 28,
                  background: "rgba(255, 149, 0, 0.22)",
                  border: "3px solid #FF9500",
                  boxShadow: "0 0 35px rgba(255, 149, 0, 0.7)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Img
                  src={staticFile("media/icon_calculator.svg")}
                  style={{ width: 105, height: 105 }}
                />
              </div>

              {/* 3. Bottom Title & Code */}
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 14, width: "100%" }}>
                <div
                  style={{
                    fontSize: 46,
                    fontWeight: 950,
                    color: "#FFFFFF",
                    textShadow: "0 0 25px rgba(255,255,255,0.7)",
                  }}
                >
                  آلة حاسبة ذكية 🧮
                </div>
                <div
                  style={{
                    padding: "8px 24px",
                    borderRadius: 14,
                    background: "rgba(0, 0, 0, 0.85)",
                    border: "1.5px solid rgba(255, 149, 0, 0.4)",
                    color: "#FFA657",
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 22,
                    fontWeight: 800,
                  }}
                >
                  def calculator(a, b, op):
                </div>
              </div>
            </div>
          )}

          {/* ========================================================= */}
          {/* PHASE 4: 3 SQUARE CARDS SHOWCASE ON ZOOM OUT (f184 - f242) */}
          {/* Matching the EXACT same internal distribution: Top Pill -> Center Badge -> Title & Code */}
          {/* ========================================================= */}
          {frame >= 184 && (
            <div
              style={{
                position: "relative",
                width: "100%",
                height: "100%",
                display: "flex",
                flexDirection: "column",
                justifyContent: "center",
                alignItems: "center",
                gap: 22,
                direction: "rtl",
                transform: `scale(${allCardsScale})`,
                opacity: allCardsOpacity,
                zIndex: 25,
              }}
            >
              {/* Top Row: 2 Square Cards Side by Side (Variables & Loops) */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "center",
                  gap: 22,
                  width: "100%",
                }}
              >
                {/* SQUARE CARD 1: Variables (Cyan) */}
                <div
                  style={{
                    width: 470,
                    height: 470,
                    borderRadius: 30,
                    background: "rgba(10, 18, 36, 0.98)",
                    border: "3px solid #00F2FE",
                    boxShadow:
                      "0 0 45px rgba(0, 242, 254, 0.5), inset 0 0 20px rgba(0, 242, 254, 0.15)",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "24px 18px 26px 18px",
                    boxSizing: "border-box",
                    textAlign: "center",
                    transform: `scale(${c1FinalSpring})`,
                  }}
                >
                  {/* 1. Top Pill */}
                  <div
                    style={{
                      padding: "6px 18px",
                      borderRadius: 16,
                      background: "rgba(0, 242, 254, 0.2)",
                      border: "1.5px solid #00F2FE",
                      color: "#FFFFFF",
                      fontSize: 16,
                      fontWeight: 900,
                      fontFamily: "'JetBrains Mono', monospace",
                      letterSpacing: 1.5,
                    }}
                  >
                    DAY 01 • VARIABLES
                  </div>

                  {/* 2. Center Badge */}
                  <div
                    style={{
                      width: 110,
                      height: 110,
                      borderRadius: 22,
                      background: "rgba(0, 242, 254, 0.2)",
                      border: "2.5px solid #00F2FE",
                      boxShadow: "0 0 25px rgba(0, 242, 254, 0.6)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: "#00F2FE",
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 34,
                      fontWeight: 950,
                    }}
                  >
                    x = 10
                  </div>

                  {/* 3. Bottom Title & Code */}
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8, width: "100%" }}>
                    <div
                      style={{
                        fontSize: 30,
                        fontWeight: 950,
                        color: "#FFFFFF",
                        lineHeight: 1.2,
                        textShadow: "0 0 20px rgba(255,255,255,0.6)",
                      }}
                    >
                      المتغيرات والبيانات
                    </div>
                    <div
                      style={{
                        padding: "6px 16px",
                        borderRadius: 10,
                        background: "rgba(0, 0, 0, 0.8)",
                        border: "1px solid rgba(0, 242, 254, 0.35)",
                        color: "#79C0FF",
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 16,
                        fontWeight: 800,
                      }}
                    >
                      name = "Python"
                    </div>
                  </div>
                </div>

                {/* SQUARE CARD 2: Loops (Emerald) */}
                <div
                  style={{
                    width: 470,
                    height: 470,
                    borderRadius: 30,
                    background: "rgba(8, 28, 20, 0.98)",
                    border: "3px solid #00FFA3",
                    boxShadow:
                      "0 0 45px rgba(0, 255, 163, 0.5), inset 0 0 20px rgba(0, 255, 163, 0.15)",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "24px 18px 26px 18px",
                    boxSizing: "border-box",
                    textAlign: "center",
                    transform: `scale(${c2FinalSpring})`,
                  }}
                >
                  {/* 1. Top Pill */}
                  <div
                    style={{
                      padding: "6px 18px",
                      borderRadius: 16,
                      background: "rgba(0, 255, 163, 0.2)",
                      border: "1.5px solid #00FFA3",
                      color: "#FFFFFF",
                      fontSize: 16,
                      fontWeight: 900,
                      fontFamily: "'JetBrains Mono', monospace",
                      letterSpacing: 1.5,
                    }}
                  >
                    DAY 05 • FOR LOOPS
                  </div>

                  {/* 2. Center Badge */}
                  <div
                    style={{
                      width: 110,
                      height: 110,
                      borderRadius: 22,
                      background: "rgba(0, 255, 163, 0.2)",
                      border: "2.5px solid #00FFA3",
                      boxShadow: "0 0 25px rgba(0, 255, 163, 0.6)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <Img
                      src={staticFile("media/icon_repeat.svg")}
                      style={{
                        width: 66,
                        height: 66,
                        transform: `rotate(${frame * 3}deg)`,
                      }}
                    />
                  </div>

                  {/* 3. Bottom Title & Code */}
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8, width: "100%" }}>
                    <div
                      style={{
                        fontSize: 30,
                        fontWeight: 950,
                        color: "#FFFFFF",
                        lineHeight: 1.2,
                        textShadow: "0 0 20px rgba(255,255,255,0.6)",
                      }}
                    >
                      اللوبات والتكرار
                    </div>
                    <div
                      style={{
                        padding: "6px 16px",
                        borderRadius: 10,
                        background: "rgba(0, 0, 0, 0.8)",
                        border: "1px solid rgba(0, 255, 163, 0.35)",
                        color: "#56D364",
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 16,
                        fontWeight: 800,
                      }}
                    >
                      for day in range(11):
                    </div>
                  </div>
                </div>
              </div>

              {/* Bottom Row: SQUARE CARD 3 Centered (Calculator) */}
              <div
                style={{
                  width: 470,
                  height: 470,
                  borderRadius: 30,
                  background: "rgba(34, 20, 6, 0.98)",
                  border: "3px solid #FF9500",
                  boxShadow:
                    "0 0 45px rgba(255, 149, 0, 0.55), inset 0 0 20px rgba(255, 149, 0, 0.15)",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "24px 18px 26px 18px",
                  boxSizing: "border-box",
                  textAlign: "center",
                  transform: `scale(${c3FinalSpring})`,
                }}
              >
                {/* 1. Top Pill */}
                <div
                  style={{
                    padding: "6px 18px",
                    borderRadius: 16,
                    background: "rgba(255, 149, 0, 0.22)",
                    border: "1.5px solid #FF9500",
                    color: "#FFFFFF",
                    fontSize: 16,
                    fontWeight: 900,
                    fontFamily: "'JetBrains Mono', monospace",
                    letterSpacing: 1.5,
                  }}
                >
                  DAY 10 • FIRST PROJECT
                </div>

                {/* 2. Center Badge */}
                <div
                  style={{
                    width: 110,
                    height: 110,
                    borderRadius: 22,
                    background: "rgba(255, 149, 0, 0.22)",
                    border: "2.5px solid #FF9500",
                    boxShadow: "0 0 25px rgba(255, 149, 0, 0.7)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <Img
                    src={staticFile("media/icon_calculator.svg")}
                    style={{ width: 70, height: 70 }}
                  />
                </div>

                {/* 3. Bottom Title & Code */}
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8, width: "100%" }}>
                  <div
                    style={{
                      fontSize: 30,
                      fontWeight: 950,
                      color: "#FFFFFF",
                      lineHeight: 1.2,
                      textShadow: "0 0 20px rgba(255,255,255,0.6)",
                    }}
                  >
                    آلة حاسبة ذكية 🧮
                  </div>
                  <div
                    style={{
                      padding: "6px 16px",
                      borderRadius: 10,
                      background: "rgba(0, 0, 0, 0.8)",
                      border: "1.5px solid rgba(255, 149, 0, 0.35)",
                      color: "#FFA657",
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 16,
                      fontWeight: 800,
                    }}
                  >
                    def calculator():
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ========================================================= */}
        {/* BOTTOM CLIMAX: "⚡ كـلـهـا بـنـفـس الـيـوم! ⚡" Cyber Neon Hero */}
        {/* ========================================================= */}
        {frame >= 184 && (
          <div
            style={{
              width: "100%",
              maxWidth: 980,
              direction: "rtl",
              display: "flex",
              justifyContent: "center",
              transform: `scale(${bannerScale})`,
              zIndex: 40,
              marginBottom: 10,
            }}
          >
            <div
              style={{
                width: "100%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 18,
                padding: "18px 30px",
                borderRadius: 32,
                background: "rgba(18, 12, 4, 0.96)",
                border: "3.5px solid #FFE600",
                boxShadow:
                  "0 0 60px rgba(255, 230, 0, 0.75), inset 0 0 30px rgba(255, 230, 0, 0.3)",
                backdropFilter: "blur(16px)",
              }}
            >
              <span style={{ fontSize: 44 }}>⚡</span>
              <span
                style={{
                  fontSize: 54,
                  fontWeight: 950,
                  color: "#FFE600",
                  letterSpacing: 1.5,
                  textShadow:
                    "0 0 40px #FFE600, 0 0 18px #FF8800, 0 0 80px #FF5500",
                }}
              >
                كـلـهـا بـنـفـس الـيـوم!
              </span>
              <span style={{ fontSize: 44 }}>⚡</span>
            </div>
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};
