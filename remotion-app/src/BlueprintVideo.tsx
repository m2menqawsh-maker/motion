import React, { useEffect, useState } from "react";
import { AbsoluteFill, Sequence, Audio, continueRender, delayRender, staticFile } from "remotion";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { slide } from "@remotion/transitions/slide";
import { fade } from "@remotion/transitions/fade";
import { wipe } from "@remotion/transitions/wipe";
import { flip } from "@remotion/transitions/flip";
import { zoomInOut } from "@remotion/transitions/zoom-in-out";
import { crossZoom } from "@remotion/transitions/cross-zoom";
import { filmBurn } from "@remotion/transitions/film-burn";
import { dissolve } from "@remotion/transitions/dissolve";
import { iris } from "@remotion/transitions/iris";
import { none } from "@remotion/transitions/none";
import { BrandProvider, BrandKit } from "../../contracts/brand";
import { loadFont } from "../../contracts/fonts";
import { TEMPLATE_REGISTRY } from "../../registry/template-registry";
import { EFFECTS_RUNTIME } from "../../registry/effects-runtime";
import { MergedProject } from "./merge";

const EngineBridge: React.FC<{ children: React.ReactNode }> = ({ children }) => <>{children}</>;

export interface BlueprintVideoProps {
  projectData: MergedProject;
  brand: BrandKit;
}

export const BlueprintVideo: React.FC<BlueprintVideoProps> = ({ projectData, brand }) => {
  const [handle] = useState(() => delayRender());
  const [fontsLoaded, setFontsLoaded] = useState(false);
  const [spectrums, setSpectrums] = useState<Record<string, number[][]>>({});

  useEffect(() => {
    const fontsToLoad = new Set<string>();
    
    // Default brand fonts
    if (brand.fonts?.display) fontsToLoad.add(brand.fonts.display);
    if (brand.fonts?.body) fontsToLoad.add(brand.fonts.body);

    projectData.scenes.forEach(scene => {
      if (scene.surface.fontFamily) {
        fontsToLoad.add(scene.surface.fontFamily);
      }
    });

    const loadAll = async () => {
      try {
        const promises = Array.from(fontsToLoad).map(f => loadFont(f as any));
        
        const specPromises = projectData.scenes.map(async (scene) => {
            const entry = TEMPLATE_REGISTRY[scene.template];
            if (entry?.consumes?.includes("spectrum") && scene.content?.audioRef) {
                const specUrl = staticFile(scene.content.audioRef.replace(/\.[^/.]+$/, "") + ".spectrum.json");
                try {
                    const res = await fetch(specUrl);
                    if (res.ok) {
                        const data = await res.json();
                        return { id: scene.scene_id, data };
                    }
                } catch (e) {
                    console.warn("Could not load spectrum for", scene.content.audioRef, e);
                }
            }
            return null;
        });

        const [...specs] = await Promise.all([...promises, ...specPromises]);
        
        const newSpecs: Record<string, number[][]> = {};
        for (const s of specs) {
            if (s && typeof s === 'object' && 'id' in s) {
                newSpecs[s.id] = s.data;
            }
        }
        setSpectrums(newSpecs);
      } catch (e) {
        console.warn("Failed to load some fonts", e);
      } finally {
        setFontsLoaded(true);
        continueRender(handle);
      }
    };

    loadAll();
  }, [projectData, brand, handle]);

  if (!fontsLoaded) {
    return null;
  }

  return (
    <BrandProvider brand={brand}>
      <AbsoluteFill style={{ backgroundColor: brand.colors?.background || "#000" }}>
        {projectData.audio?.voiceover && (
          <Audio src={staticFile(projectData.audio.voiceover)} volume={1.0} />
        )}
        {projectData.audio?.bgm && (
          <Audio src={staticFile(projectData.audio.bgm)} volume={projectData.audio.bgmVolume ?? 0.15} />
        )}
        
        <TransitionSeries>
        {projectData.scenes.map((scene, idx) => {
          const entry = TEMPLATE_REGISTRY[scene.template];
          if (!entry) return null;

          const Component = entry.component;

          // معالجة الصوت والموسيقى
          const voAudio = scene.sfx_ref ? (
             <Audio src={staticFile(scene.sfx_ref)} />
          ) : null;

          const surfaceProps = { ...scene.surface };
          
          let content: any = { ...scene.content };
          if (entry.consumes && entry.consumes.length > 0) {
            if (entry.consumes.includes("lines") && surfaceProps.text && !content.lines) {
              content.lines = surfaceProps.text.split("\n");
            }
            if (entry.consumes.includes("images") && scene.media_refs && !content.images) {
              content.images = [...scene.media_refs];
            }
            if (entry.consumes.includes("screen") && scene.media_refs && scene.media_refs.length > 0 && !content.screen) {
              content.screen = scene.media_refs[0];
            }
            if (entry.consumes.includes("words") && scene.captions_ref && !content.words) {
              content.words = [];
            }
            if (entry.consumes.includes("spectrum") && spectrums[scene.scene_id]) {
              content.spectrum = spectrums[scene.scene_id];
            }
          }

          let element = <Component surface={surfaceProps} content={content} template_props={scene.template_props} />;
          let overlays: React.ReactNode[] = [];

          if (scene.effects && scene.effects.length > 0) {
             const wrappers = scene.effects.filter((e: any) => e.apply === "scene" || EFFECTS_RUNTIME[e.effect]?.kind === "wrapper");
             const applyingOverlays = scene.effects.filter((e: any) => e.apply === "overlay" || EFFECTS_RUNTIME[e.effect]?.kind === "overlay");
             
             element = wrappers.reduceRight((acc: any, effectDef: any) => {
                 const runtime = EFFECTS_RUNTIME[effectDef.effect];
                 if (!runtime || !runtime.component) return acc;
                 const EffectComp = runtime.component;
                 return <EffectComp {...effectDef.params}>{acc}</EffectComp>;
             }, element);
             
             overlays = applyingOverlays.map((effectDef: any, eidx: number) => {
                 const runtime = EFFECTS_RUNTIME[effectDef.effect];
                 if (!runtime || !runtime.component) return null;
                 const EffectComp = runtime.component;
                 return (
                    <AbsoluteFill key={`overlay-${eidx}`}>
                       <EffectComp {...effectDef.params} />
                    </AbsoluteFill>
                 );
             });
          }

          // Determine presentation based on string
          let presentation = fade();
          if (scene.transition && scene.transition.type) {
             const type = scene.transition.type;
             if (type === "slide") presentation = slide();
             else if (type === "wipe") presentation = wipe();
             else if (type === "flip") presentation = flip();
             else if (type === "zoom") presentation = zoomInOut();
             else if (type === "cross-zoom") presentation = crossZoom();
             else if (type === "film-burn") presentation = filmBurn();
             else if (type === "dissolve") presentation = dissolve();
             else if (type === "iris") presentation = iris();
             else if (type === "none") presentation = none();
          }

          return (
            <React.Fragment key={`${scene.scene_id}-${idx}`}>
              <TransitionSeries.Sequence 
                durationInFrames={scene.durationFrames}
              >
                <EngineBridge>
                  {element}
                  {overlays}
                  {voAudio}
                </EngineBridge>
              </TransitionSeries.Sequence>
              
              {idx < projectData.scenes.length - 1 && scene.transition && (
                <TransitionSeries.Transition
                  presentation={presentation}
                  timing={linearTiming({ durationInFrames: scene.transition.durationFrames || 15 })}
                />
              )}
            </React.Fragment>
          );
        })}
        </TransitionSeries>
      </AbsoluteFill>
    </BrandProvider>
  );
};
