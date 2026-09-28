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
import { validateTemplatePayload } from "../../contracts/template-schemas";
import { UnknownEffectError, UnknownTransitionError, UnknownTemplateError } from "../../contracts/render-input";

const EngineBridge: React.FC<{ children: React.ReactNode }> = ({ children }) => <>{children}</>;

export interface BlueprintVideoProps {
  projectData: MergedProject;
  brand: BrandKit;
}

export const BlueprintVideo: React.FC<BlueprintVideoProps> = ({ projectData, brand }) => {
  // Pre-mount fail-closed validations (S16 - LED-043, LED-045, LED-046)
  if (projectData && projectData.scenes) {
    for (let idx = 0; idx < projectData.scenes.length; idx++) {
      const scene = projectData.scenes[idx];
      const entry = TEMPLATE_REGISTRY[scene.template];
      if (!entry) {
        throw new UnknownTemplateError(scene.template, scene.scene_id);
      }

      if (scene.effects && scene.effects.length > 0) {
        for (const eff of scene.effects) {
          if (!EFFECTS_RUNTIME[eff.effect]) {
            throw new UnknownEffectError(eff.effect, scene.scene_id);
          }
        }
      }

      if (scene.transition) {
        const validTypes = ["fade", "slide", "wipe", "flip", "zoom", "cross-zoom", "film-burn", "dissolve", "iris", "none"];
        if (!validTypes.includes(scene.transition.type)) {
          throw new UnknownTransitionError(scene.transition.type, scene.scene_id);
        }
      }

      validateTemplatePayload(entry, scene, `scene[${idx}] ('${scene.scene_id}')`);
    }
  }

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
              const audioPath = typeof scene.content.audioRef === "string"
                ? scene.content.audioRef
                : (scene.content.audioRef as any)?.url || (scene.content.audioRef as any)?.asset_id || "";
              const specUrl = staticFile(audioPath.replace(/\.[^/.]+$/, "") + ".spectrum.json");
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
          if (!entry) {
            throw new UnknownTemplateError(scene.template, scene.scene_id);
          }

          // Validate effects fail-closed before mounting (S16 - LED-046)
          if (scene.effects && scene.effects.length > 0) {
            for (const eff of scene.effects) {
              if (!EFFECTS_RUNTIME[eff.effect]) {
                throw new UnknownEffectError(eff.effect, scene.scene_id);
              }
            }
          }

          // Validate transition fail-closed before mounting (S16 - LED-043)
          if (scene.transition) {
            const validTypes = ["fade", "slide", "wipe", "flip", "zoom", "cross-zoom", "film-burn", "dissolve", "iris", "none"];
            if (!validTypes.includes(scene.transition.type)) {
              throw new UnknownTransitionError(scene.transition.type, scene.scene_id);
            }
          }

          // Validate template payload fail-closed before mounting (S16 - LED-045)
          validateTemplatePayload(entry, scene);

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

          // Determine presentation based on transition type (S16 - LED-043)
          let presentation: any = fade({} as any);
          if (scene.transition && scene.transition.type) {
             const type = scene.transition.type;
             if (type === "slide") presentation = slide({} as any);
             else if (type === "wipe") presentation = wipe({} as any);
             else if (type === "flip") presentation = flip({} as any);
             else if (type === "zoom") presentation = zoomInOut({} as any);
             else if (type === "cross-zoom") presentation = crossZoom({} as any);
             else if (type === "film-burn") presentation = filmBurn({} as any);
             else if (type === "dissolve") presentation = dissolve({} as any);
             else if (type === "iris") presentation = iris({} as any);
             else if (type === "none") presentation = none({} as any);
             else if (type === "fade") presentation = fade({} as any);
             else {
               throw new UnknownTransitionError(type, scene.scene_id);
             }
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
