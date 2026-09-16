---
name: remotion-best-practices
description: Router for all Remotion skills
version: 4.0.509
---

## Preserve user changes

Users may make edits in the code outside of the conversation.

If you detect a surprising change made in the meanwhile, don't overwrite it, assume it was intentional or ask for confirmation.

## Creating a video

If the user asks to make, create, or build a new video or composition, load [Create a new Remotion video](./create/SKILL.md), whether or not a Remotion project already exists.
If no Remotion project currently exists, load [Create a new Remotion project](./create/SKILL.md)

## React Markup Best Practices

If you are writing Remotion React Markup, load [Remotion Markup Best Practices](./markup/SKILL.md)

## Maps

For static maps, animated routes and markers, geographic explainers, Mapbox, MapLibre, MapTiler, GeoJSON, or 3D geographic flyovers, load [Remotion Maps](./maps/SKILL.md).

## Multimedia

For achieving multimedia tasks in the browser, such as trimming, cropping videos, or getting metadata from them, load [Remotion Multimedia](./multimedia/SKILL.md)

## Improving Interactivity

By structuring the Remotion markup well, we can allow users to interactively change things in the Studio and write back to code. If relevant: [Interactivity Best Practices](./interactivity/SKILL.md)

## Rendering

For advanced rendering beyond simple `npx remotion render`, see: [Rendering Best Practices](./render/SKILL.md)

## Opening Remotion Studio

To launch a project in Remotion Studio, open its exact local URL, or configure Studio CLI flags, load [Remotion Studio](./studio/SKILL.md).

## Captions

When working with Captions, load [Remotion Captions](./captions/SKILL.md).

## Creating a SaaS, automation or application

Use the [Remotion SaaS skill](./saas/SKILL.md) for knowledge about Remotion-powered SaaS apps, such as `<Player>`, rendering on Lambda, Vercel, Cloudflare, via Express.js, client-side rendering, or for finding the right SaaS template.

## Looking up Remotion APIs and documentation

To find and read current Remotion documentation, load [Remotion Docs](./docs/SKILL.md).

## Upgrading

To upgrade Remotion, related packages, compatible Mediabunny packages, and installed Remotion Agent Skills, load [Remotion Upgrade](./upgrade/SKILL.md).
