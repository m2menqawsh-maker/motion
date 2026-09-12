import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  OffthreadVideo,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

export const SURGICAL_AD_DURATION_FRAMES = 900; // 30.0s @ 30fps

export const SurgicalSutureAd: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Background Music with gentle ducking when speech is active
  const isSpeechActive =
    (frame >= 6 && frame <= 115) ||
    (frame >= 135 && frame <= 315) ||
    (frame >= 320 && frame <= 425) ||
    (frame >= 440 && frame <= 525) ||
    (frame >= 545 && frame <= 680) ||
    (frame >= 690 && frame <= 755);

  const musicVolume = interpolate(
    frame,
    [0, 30, 870, 900],
    [0, isSpeechActive ? 0.18 : 0.32, isSpeechActive ? 0.18 : 0.32, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Persistent Logo Fade Out when Video 3 expands to full screen (frames 625 - 665)
  const logoOpacity = interpolate(frame, [625, 665], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#FFFFFF",
        fontFamily:
          "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif, -apple-system",
        overflow: "hidden",
      }}
    >
      {/* 1. Global White Topography Background Video Layer */}
      <AbsoluteFill style={{ zIndex: 1 }}>
        <OffthreadVideo
          src={staticFile("BG_intra.mp4")}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            opacity: 0.95,
          }}
          startFrom={0}
          endAt={900}
        />
      </AbsoluteFill>

      {/* 2. Audio Layer - Background Music */}
      <Audio src={staticFile("music_30s.mp3")} volume={musicVolume} />

      {/* --- 6 VOICEOVER SENTENCES (100% Synced 1:1 with the 6 Shots) --- */}
      {/* VO 1 (Shot 1: 0.0s - 4.5s): "حابب تتقن الغرز الجراحية عملياً؟" */}
      <Sequence from={6} durationInFrames={115}>
        <Audio src={staticFile("vo_1.wav")} volume={1.0} />
      </Sequence>

      {/* VO 2 (Shot 2: 4.5s - 10.5s): "ورشة الغرز وأنواع الخيوط مع المدرب محمد محمود أبو رحمه من شركة كوما" */}
      <Sequence from={135} durationInFrames={195}>
        <Audio src={staticFile("vo_2.wav")} volume={1.0} />
      </Sequence>

      {/* VO 3 (Shot 3: 10.5s - 14.5s): "الأدوات والخيوط مشمولة بالكامل" */}
      <Sequence from={315} durationInFrames={110}>
        <Audio src={staticFile("vo_3.wav")} volume={1.0} />
      </Sequence>

      {/* VO 4 (Shot 4: 14.5s - 18.0s): "والمجموعة محدودة العدد" */}
      <Sequence from={435} durationInFrames={80}>
        <Audio src={staticFile("vo_4.wav")} volume={1.0} />
      </Sequence>

      {/* VO 5 (Shot 5: 18.0s - 23.0s): "الرسوم 35 شيكل شاملة كل شيء" */}
      <Sequence from={540} durationInFrames={140}>
        <Audio src={staticFile("vo_5.wav")} volume={1.0} />
      </Sequence>

      {/* VO 6 (Shot 6: 23.0s - 30.0s): "احجز مقعدك الآن" */}
      <Sequence from={690} durationInFrames={75}>
        <Audio src={staticFile("vo_6.wav")} volume={1.0} />
      </Sequence>

      {/* --- SYNCHRONIZED MOTION GRAPHICS SOUND EFFECTS (SFX) --- */}
      {/* SFX: Shot 1 Video 1 Shrink & Kinetic Pop */}
      <Sequence from={48} durationInFrames={35}>
        <Audio src={staticFile("whoosh_cinematic.mp3")} volume={0.6} />
      </Sequence>

      {/* SFX: Shot 1 "عملياً؟" Word Accent Chime */}
      <Sequence from={71} durationInFrames={45}>
        <Audio src={staticFile("accent_chime.mp3")} volume={0.8} />
      </Sequence>

      {/* SFX: Shot 1 Exit Transition Whoosh */}
      <Sequence from={120} durationInFrames={30}>
        <Audio src={staticFile("whoosh_cinematic.mp3")} volume={0.55} />
      </Sequence>

      {/* SFX: Shot 2 Trainer Hero Slide & Camera Focus Shutter */}
      <Sequence from={135} durationInFrames={30}>
        <Audio src={staticFile("camera_click.mp3")} volume={0.7} />
      </Sequence>

      {/* SFX: Shot 2 Accent Chime for Trainer Name */}
      <Sequence from={200} durationInFrames={40}>
        <Audio src={staticFile("accent_chime.mp3")} volume={0.6} />
      </Sequence>

      {/* SFX: Shot 2 Exit Transition Whoosh */}
      <Sequence from={300} durationInFrames={30}>
        <Audio src={staticFile("whoosh_cinematic.mp3")} volume={0.55} />
      </Sequence>

      {/* SFX: Shot 3 Training Video Entrance Whoosh */}
      <Sequence from={315} durationInFrames={35}>
        <Audio src={staticFile("whoosh_cinematic.mp3")} volume={0.6} />
      </Sequence>

      {/* SFX: Shot 3 Inclusions Card Accent Bell */}
      <Sequence from={340} durationInFrames={45}>
        <Audio src={staticFile("accent_chime.mp3")} volume={0.75} />
      </Sequence>

      {/* SFX: Shot 3 Exit Transition Whoosh */}
      <Sequence from={420} durationInFrames={30}>
        <Audio src={staticFile("whoosh_cinematic.mp3")} volume={0.55} />
      </Sequence>

      {/* SFX: Shot 4 Scarcity Warning Accent */}
      <Sequence from={435} durationInFrames={45}>
        <Audio src={staticFile("accent_chime.mp3")} volume={0.75} />
      </Sequence>

      {/* SFX: Shot 4 Exit Transition Whoosh */}
      <Sequence from={525} durationInFrames={30}>
        <Audio src={staticFile("whoosh_cinematic.mp3")} volume={0.55} />
      </Sequence>

      {/* SFX: Shot 5 Tools Video Entrance Whoosh */}
      <Sequence from={540} durationInFrames={35}>
        <Audio src={staticFile("whoosh_cinematic.mp3")} volume={0.6} />
      </Sequence>

      {/* SFX: Shot 5 Fullscreen Scale Expansion Whoosh */}
      <Sequence from={630} durationInFrames={50}>
        <Audio src={staticFile("whoosh_cinematic.mp3")} volume={0.75} />
      </Sequence>

      {/* 3. Persistent Header Logo Badge Layer (Visible during shots 1-5 until fullscreen expansion) */}
      {frame < 665 && (
        <div
          style={{
            position: "absolute",
            top: 70,
            left: 0,
            right: 0,
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            zIndex: 35,
            opacity: logoOpacity,
          }}
        >
          <div
            style={{
              width: 170,
              height: 170,
              borderRadius: "50%",
              backgroundColor: "#FFFFFF",
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              boxShadow:
                "0 14px 40px rgba(11, 60, 93, 0.25), 0 0 0 5px rgba(2, 136, 209, 0.2)",
              padding: 22,
            }}
          >
            <Img
              src={staticFile("logo.svg")}
              style={{
                width: "100%",
                height: "100%",
                objectFit: "contain",
              }}
            />
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* SHOT 1 (Frames 0 - 135): Live Hook Video 1 -> Scaled Card + Kinetic Words */}
      {/* ========================================================================= */}
      <Sequence from={0} durationInFrames={135}>
        <Shot1Hook fps={fps} />
      </Sequence>

      {/* ========================================================================= */}
      {/* SHOT 2 (Frames 135 - 315): Hero Trainer Cutout & Workshop Title            */}
      {/* ========================================================================= */}
      <Sequence from={135} durationInFrames={180}>
        <Shot2Trainer fps={fps} />
      </Sequence>

      {/* ========================================================================= */}
      {/* SHOT 3 (Frames 315 - 435): Practical Training Video & All-Inclusive Card   */}
      {/* ========================================================================= */}
      <Sequence from={315} durationInFrames={120}>
        <Shot3Training fps={fps} />
      </Sequence>

      {/* ========================================================================= */}
      {/* SHOT 4 (Frames 435 - 540): Scarcity & Limited Seats Motion Graphics        */}
      {/* ========================================================================= */}
      <Sequence from={435} durationInFrames={105}>
        <Shot4Scarcity fps={fps} />
      </Sequence>

      {/* ========================================================================= */}
      {/* SHOTS 5 & 6 (Frames 540 - 900): Tools Video Expanding to Fullscreen + CTA  */}
      {/* ========================================================================= */}
      <Sequence from={540} durationInFrames={360}>
        <SeamlessVideoSection fps={fps} />
      </Sequence>
    </AbsoluteFill>
  );
};

/* -------------------------------------------------------------------------- */
/* Shot 1: First 1.8s Fullscreen Hook Video 1, then Shrinks + Word-by-word VO */
/* -------------------------------------------------------------------------- */
const Shot1Hook: React.FC<{ fps: number }> = ({ fps }) => {
  const frame = useCurrentFrame(); // 0 to 134

  // Video 1 shrinks from Fullscreen (100%) to Floating Card (90%) between frames 48 and 72 (1.6s to 2.4s)
  const shrinkProgress = interpolate(frame, [48, 72], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const videoWidth = interpolate(shrinkProgress, [0, 1], [100, 90]);
  const videoHeight = interpolate(shrinkProgress, [0, 1], [100, 52]);
  const videoBorderRadius = interpolate(shrinkProgress, [0, 1], [0, 36]);
  const videoTop = interpolate(shrinkProgress, [0, 1], [0, 240]);

  // Word timestamps (relative to frame 0)
  // "حابب" (0.21s / frame 6)
  // "تتقن" (0.75s / frame 23)
  // "الغرز" (1.23s / frame 37)
  // "الجراحية" (1.67s / frame 50)
  // "عملياً؟" (2.35s / frame 71)

  const word1Spring = spring({ frame: Math.max(0, frame - 6), fps, config: { damping: 13, mass: 0.7 } });
  const word2Spring = spring({ frame: Math.max(0, frame - 23), fps, config: { damping: 13, mass: 0.7 } });
  const word3Spring = spring({ frame: Math.max(0, frame - 37), fps, config: { damping: 13, mass: 0.7 } });
  const word4Spring = spring({ frame: Math.max(0, frame - 50), fps, config: { damping: 13, mass: 0.7 } });
  const burstSpring = spring({ frame: Math.max(0, frame - 71), fps, config: { damping: 11, mass: 0.5 } });

  // Exit transition (frames 118 to 134)
  const exitProgress = interpolate(frame, [118, 134], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const exitScale = interpolate(exitProgress, [0, 1], [1, 0.88]);
  const exitOpacity = interpolate(exitProgress, [0, 1], [1, 0]);

  const glowPulse = frame >= 71 ? Math.sin((frame - 71) * 0.22) * 12 + 20 : 0;

  return (
    <AbsoluteFill
      style={{
        zIndex: 10,
        opacity: exitOpacity,
        transform: `scale(${exitScale})`,
        overflow: "hidden",
      }}
    >
      {/* 1. Live Hook Video 1 (Full screen first, then shrinks to card) */}
      <div
        style={{
          position: "absolute",
          top: `${videoTop}px`,
          left: `${(100 - videoWidth) / 2}%`,
          width: `${videoWidth}%`,
          height: `${videoHeight}%`,
          borderRadius: `${videoBorderRadius}px`,
          overflow: "hidden",
          boxShadow:
            shrinkProgress > 0.1
              ? "0 25px 60px rgba(11, 60, 93, 0.35), 0 0 0 4px rgba(2, 136, 209, 0.3)"
              : "none",
          transition: "border-radius 0.1s linear",
        }}
      >
        <OffthreadVideo
          src={staticFile("video1_intra.mp4")}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
          startFrom={0}
          endAt={140}
        />
      </div>

      {/* 2. Word-by-Word Kinetic Typography Overlay (Positioned in lower area) */}
      <div
        style={{
          position: "absolute",
          bottom: 120,
          left: 40,
          right: 40,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          textAlign: "center",
          gap: 16,
          zIndex: 25,
        }}
      >
        {/* Row 1: "حابب تتقن" */}
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            gap: 20,
          }}
        >
          {frame >= 6 && (
            <span
              style={{
                fontSize: 84,
                fontWeight: 900,
                color: "#0B3C5D",
                transform: `scale(${word1Spring})`,
                display: "inline-block",
                textShadow: "0 4px 20px rgba(255, 255, 255, 0.9)",
              }}
            >
              حابب
            </span>
          )}
          {frame >= 23 && (
            <span
              style={{
                fontSize: 84,
                fontWeight: 900,
                color: "#0B3C5D",
                transform: `scale(${word2Spring})`,
                display: "inline-block",
                textShadow: "0 4px 20px rgba(255, 255, 255, 0.9)",
              }}
            >
              تتقن
            </span>
          )}
        </div>

        {/* Row 2: "الغرز الجراحية" */}
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            gap: 20,
          }}
        >
          {frame >= 37 && (
            <span
              style={{
                fontSize: 96,
                fontWeight: 900,
                color: "#0288D1",
                transform: `scale(${word3Spring})`,
                display: "inline-block",
                textShadow: "0 6px 30px rgba(2, 136, 209, 0.4)",
              }}
            >
              الغرز
            </span>
          )}
          {frame >= 50 && (
            <span
              style={{
                fontSize: 96,
                fontWeight: 900,
                color: "#0288D1",
                transform: `scale(${word4Spring})`,
                display: "inline-block",
                textShadow: "0 6px 30px rgba(2, 136, 209, 0.4)",
              }}
            >
              الجراحية
            </span>
          )}
        </div>

        {/* Row 3: "عملياً؟ 🩺" Explosive Burst Badge */}
        {frame >= 71 && (
          <div
            style={{
              marginTop: 14,
              transform: `scale(${burstSpring})`,
              opacity: interpolate(burstSpring, [0, 1], [0, 1]),
            }}
          >
            <div
              style={{
                display: "inline-block",
                padding: "22px 75px",
                borderRadius: 40,
                background: "linear-gradient(135deg, #0288D1 0%, #0B3C5D 100%)",
                boxShadow: `0 20px 60px rgba(2, 136, 209, 0.5), 0 0 ${glowPulse}px rgba(2, 136, 209, 0.9)`,
                color: "#FFFFFF",
                fontSize: 94,
                fontWeight: 900,
                letterSpacing: "1px",
                border: "4px solid #FFFFFF",
              }}
            >
              عملياً؟ 🩺
            </div>
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};

/* -------------------------------------------------------------------------- */
/* Shot 2: Hero Trainer Cutout & Clean Name Card                              */
/* -------------------------------------------------------------------------- */
const Shot2Trainer: React.FC<{ fps: number }> = ({ fps }) => {
  const frame = useCurrentFrame();

  const trainerEnterSpring = spring({ frame, fps, config: { damping: 15, mass: 0.8 } });
  const cardEnterSpring = spring({ frame: Math.max(0, frame - 18), fps, config: { damping: 14, mass: 0.8 } });

  // Exit transition (frames 160 to 180)
  const exitProgress = interpolate(frame, [160, 180], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const exitOpacity = interpolate(exitProgress, [0, 1], [1, 0]);
  const exitScale = interpolate(exitProgress, [0, 1], [1, 0.9]);

  return (
    <AbsoluteFill
      style={{
        zIndex: 10,
        overflow: "hidden",
        opacity: exitOpacity,
        transform: `scale(${exitScale})`,
      }}
    >
      {/* Hero Trainer Cutout Image */}
      <div
        style={{
          position: "absolute",
          bottom: 180,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          alignItems: "flex-end",
          transform: `translateY(${interpolate(trainerEnterSpring, [0, 1], [400, 0])}px)`,
          opacity: interpolate(trainerEnterSpring, [0, 1], [0, 1]),
          zIndex: 12,
        }}
      >
        <Img
          src={staticFile("trainer.png")}
          style={{
            height: 1250,
            width: "auto",
            objectFit: "contain",
            filter: "drop-shadow(0 30px 45px rgba(11, 60, 93, 0.45))",
          }}
        />
      </div>

      {/* Trainer Card */}
      <div
        style={{
          position: "absolute",
          bottom: 60,
          left: 45,
          right: 45,
          zIndex: 20,
          transform: `scale(${cardEnterSpring})`,
          opacity: interpolate(cardEnterSpring, [0, 1], [0, 1]),
        }}
      >
        <div
          style={{
            backgroundColor: "rgba(255, 255, 255, 0.96)",
            backdropFilter: "blur(16px)",
            borderRadius: 36,
            padding: "28px 36px",
            boxShadow:
              "0 24px 60px rgba(11, 60, 93, 0.3), 0 0 0 3px rgba(2, 136, 209, 0.35)",
            textAlign: "center",
          }}
        >
          <div style={{ fontSize: 36, fontWeight: 800, color: "#0288D1", marginBottom: 8 }}>
            ورشة الغرز وأنواع الخيوط
          </div>
          <div style={{ fontSize: 48, fontWeight: 900, color: "#0B3C5D", lineHeight: 1.2 }}>
            المدرب محمد محمود أبو رحمه
          </div>
          <div
            style={{
              marginTop: 14,
              display: "inline-block",
              backgroundColor: "#0B3C5D",
              color: "#FFFFFF",
              padding: "8px 30px",
              borderRadius: 24,
              fontSize: 28,
              fontWeight: 800,
              boxShadow: "0 6px 20px rgba(11, 60, 93, 0.25)",
            }}
          >
            من شركة كوما
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* -------------------------------------------------------------------------- */
/* Shot 3: Live Training Video 2 & Inclusions Card                            */
/* -------------------------------------------------------------------------- */
const Shot3Training: React.FC<{ fps: number }> = ({ fps }) => {
  const frame = useCurrentFrame();

  const enterSpring = spring({ frame, fps, config: { damping: 14, mass: 0.8 } });
  const cardSpring = spring({ frame: Math.max(0, frame - 15), fps, config: { damping: 13, mass: 0.7 } });

  // Exit transition (frames 102 to 120)
  const exitProgress = interpolate(frame, [102, 120], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const exitScale = interpolate(exitProgress, [0, 1], [1, 0.88]);
  const exitOpacity = interpolate(exitProgress, [0, 1], [1, 0]);

  return (
    <AbsoluteFill
      style={{
        zIndex: 10,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        padding: "0 40px",
        opacity: exitOpacity,
        transform: `scale(${exitScale})`,
      }}
    >
      <div
        style={{
          width: "100%",
          height: 1200,
          borderRadius: 44,
          overflow: "hidden",
          boxShadow:
            "0 30px 70px rgba(11, 60, 93, 0.4), 0 0 0 5px rgba(2, 136, 209, 0.45)",
          transform: `scale(${enterSpring})`,
          opacity: interpolate(enterSpring, [0, 1], [0, 1]),
          position: "relative",
        }}
      >
        <OffthreadVideo
          src={staticFile("video2_intra.mp4")}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
          startFrom={0}
          endAt={140}
        />

        {/* Large Bold Inclusions Banner on the Video */}
        <div
          style={{
            position: "absolute",
            bottom: 36,
            left: 24,
            right: 24,
            backgroundColor: "rgba(0, 137, 123, 0.95)",
            backdropFilter: "blur(14px)",
            padding: "24px 30px",
            borderRadius: 30,
            textAlign: "center",
            color: "#FFFFFF",
            boxShadow: "0 14px 35px rgba(0, 0, 0, 0.35)",
            border: "3px solid #FFFFFF",
            transform: `scale(${cardSpring})`,
          }}
        >
          <div style={{ fontSize: 44, fontWeight: 900 }}>الأدوات والخيوط 🩺</div>
          <div style={{ fontSize: 36, fontWeight: 800, marginTop: 4, opacity: 0.95 }}>
            مشمولة بالكامل ✓
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* -------------------------------------------------------------------------- */
/* Shot 4: Scarcity & Limited Seats Warning Motion Graphics                   */
/* -------------------------------------------------------------------------- */
const Shot4Scarcity: React.FC<{ fps: number }> = ({ fps }) => {
  const frame = useCurrentFrame();

  const cardSpring = spring({ frame, fps, config: { damping: 12, mass: 0.6 } });

  // Exit transition (frames 88 to 105)
  const exitProgress = interpolate(frame, [88, 105], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const exitOpacity = interpolate(exitProgress, [0, 1], [1, 0]);
  const exitScale = interpolate(exitProgress, [0, 1], [1, 0.88]);

  const warnPulse = Math.sin(frame * 0.25) * 10 + 20;

  return (
    <AbsoluteFill
      style={{
        zIndex: 10,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        padding: "0 45px",
        opacity: exitOpacity,
        transform: `scale(${exitScale})`,
      }}
    >
      <div
        style={{
          width: "100%",
          backgroundColor: "#FFF3E0",
          borderRadius: 44,
          padding: "54px 40px",
          boxShadow: `0 24px 60px rgba(230, 81, 0, 0.35), 0 0 ${warnPulse}px rgba(230, 81, 0, 0.75)`,
          border: "5px solid #E65100",
          display: "flex",
          alignItems: "center",
          gap: 32,
          transform: `scale(${cardSpring})`,
          opacity: interpolate(cardSpring, [0, 1], [0, 1]),
        }}
      >
        <div
          style={{
            width: 120,
            height: 120,
            borderRadius: "50%",
            backgroundColor: "#FFE0B2",
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            flexShrink: 0,
          }}
        >
          <Img src={staticFile("warning.svg")} style={{ width: 80, height: 80 }} />
        </div>
        <div style={{ textAlign: "right", flex: 1 }}>
          <div style={{ fontSize: 54, fontWeight: 900, color: "#E65100", lineHeight: 1.2 }}>
            المجموعة
          </div>
          <div style={{ fontSize: 46, fontWeight: 900, color: "#D32F2F", marginTop: 8 }}>
            محدودة العدد ⚠️
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* -------------------------------------------------------------------------- */
/* Shots 5 & 6: Tools Video Expands to Fullscreen -> Seamless Video 4 (CTA)   */
/* -------------------------------------------------------------------------- */
const SeamlessVideoSection: React.FC<{ fps: number }> = ({ fps }) => {
  const frame = useCurrentFrame(); // 0 to 359

  // In frames 75 to 149 (global 615 to 689), video scales smoothly to 100% full screen
  const expandProgress = interpolate(frame, [75, 149], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const isFullscreen = frame >= 149;

  const widthPct = interpolate(expandProgress, [0, 1], [92, 100]);
  const heightPct = interpolate(expandProgress, [0, 1], [74, 100]);
  const borderRadius = interpolate(expandProgress, [0, 1], [40, 0]);
  const borderWidth = interpolate(expandProgress, [0, 1], [5, 0]);

  return (
    <AbsoluteFill
      style={{
        zIndex: 10,
        backgroundColor: "transparent",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        overflow: "hidden",
      }}
    >
      {/* Continuous Video Stream over White Topography Backdrop */}
      <div
        style={{
          width: isFullscreen ? "100%" : `${widthPct}%`,
          height: isFullscreen ? "100%" : `${heightPct}%`,
          borderRadius: isFullscreen ? 0 : `${borderRadius}px`,
          overflow: "hidden",
          boxShadow: isFullscreen ? "none" : "0 30px 70px rgba(11, 60, 93, 0.4)",
          border:
            !isFullscreen && borderWidth > 0.5
              ? `${borderWidth}px solid rgba(2, 136, 209, 0.45)`
              : "none",
          position: "relative",
        }}
      >
        <OffthreadVideo
          src={staticFile("video3_4_seamless.mp4")}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
          startFrom={0}
          endAt={360}
        />
      </div>
    </AbsoluteFill>
  );
};
