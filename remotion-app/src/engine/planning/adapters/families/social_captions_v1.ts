import { AdapterContext, AdapterResult, AdapterDefinition } from '../types';

export const social_captions_v1: AdapterDefinition = {
  capability: 'social_captions_v1',
  version: '1.0',
  requiredSemanticInputs: [],
  canAdapt: (context: AdapterContext) => {
    // If it reached this adapter via registry routing, we can adapt it.
    // The main verification is that we have an expected props schema.
    return true;
  },
  adapt: (context: AdapterContext): AdapterResult => {
    const rawCaptions = context.content.captions;
    const rawTranscript = context.content.transcript;
    const rawWords = context.content.words;

    // Determine the source of captions
    let sourceCaptions: any[] = [];
    if (Array.isArray(rawCaptions)) {
      sourceCaptions = rawCaptions;
    } else if (Array.isArray(rawTranscript)) {
      sourceCaptions = rawTranscript;
    } else if (Array.isArray(rawWords)) {
      sourceCaptions = rawWords;
    }

    // Transform them to the required `@remotion/captions` format:
    // { text: string, startMs: number, endMs: number, timestampMs: number, confidence: number }
    const mappedCaptions = sourceCaptions.map((cap) => {
      return {
        text: typeof cap.text === 'string' ? cap.text : typeof cap.word === 'string' ? cap.word : '',
        startMs: typeof cap.startMs === 'number' ? cap.startMs : typeof cap.start === 'number' ? cap.start : 0,
        endMs: typeof cap.endMs === 'number' ? cap.endMs : typeof cap.end === 'number' ? cap.end : 0,
        timestampMs: typeof cap.timestampMs === 'number' ? cap.timestampMs : typeof cap.startMs === 'number' ? cap.startMs : typeof cap.start === 'number' ? cap.start : 0,
        confidence: typeof cap.confidence === 'number' ? cap.confidence : 1,
      };
    }).filter(c => c.text !== ''); // Do not invent text! Just filter invalid ones

    // If no captions were found, we provide an empty array, 
    // because the templates (SocialClip) treat `captions` as optional but semantically expect an array.
    const captionsProp = mappedCaptions;

    return {
      props: {
        ...context.content,
        captions: captionsProp
      }
    };
  }
};
