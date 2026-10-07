/**
 * preview/dom-driver.ts — Browser DOM Preview Driver.
 * S28-R06: Renders VisualFrame representations into standard DOM container
 * with aspect-fit viewport scaling, layer DOM recycling, and explicit
 * diagnostic overlays for unsupported capabilities.
 * ZERO React or Remotion runtime dependencies.
 */
import type { VisualFrame, VisualNode, CanvasDimensions } from "./types";

export interface DOMPreviewDriverOptions {
  container: HTMLElement;
  showDiagnosticsOverlay?: boolean;
}

export class DOMPreviewDriver {
  private container: HTMLElement;
  private stageWrapper: HTMLElement;
  private layerContainer: HTMLElement;
  private diagnosticOverlay: HTMLElement | null = null;
  private showDiagnosticsOverlay: boolean;
  private activeElementMap = new Map<string, HTMLElement>();

  constructor(options: DOMPreviewDriverOptions) {
    this.container = options.container;
    this.showDiagnosticsOverlay = options.showDiagnosticsOverlay ?? true;

    // 1. Setup container styles
    this.container.style.position = "relative";
    this.container.style.overflow = "hidden";
    this.container.style.display = "flex";
    this.container.style.alignItems = "center";
    this.container.style.justifyContent = "center";
    this.container.style.backgroundColor = "#0b0f19";

    // 2. Setup Stage Wrapper (Canvas Viewport)
    this.stageWrapper = this.container.ownerDocument.createElement("div");
    this.stageWrapper.className = "cv-preview-stage";
    this.stageWrapper.style.position = "absolute";
    this.stageWrapper.style.transformOrigin = "center center";
    this.stageWrapper.style.overflow = "hidden";
    this.stageWrapper.style.backgroundColor = "#000000";
    this.stageWrapper.style.boxShadow = "0 10px 30px rgba(0,0,0,0.5)";

    // 3. Layer container inside stage
    this.layerContainer = this.container.ownerDocument.createElement("div");
    this.layerContainer.className = "cv-preview-layers";
    this.layerContainer.style.position = "absolute";
    this.layerContainer.style.width = "100%";
    this.layerContainer.style.height = "100%";
    this.layerContainer.style.left = "0";
    this.layerContainer.style.top = "0";

    this.stageWrapper.appendChild(this.layerContainer);
    this.container.appendChild(this.stageWrapper);
  }

  /**
   * Renders the supplied VisualFrame into the DOM stage.
   */
  public renderFrame(frame: VisualFrame): void {
    // 1. Update stage dimensions and viewport scale
    this.updateViewportScale(frame.dimensions);

    // 2. Track elements present in this frame for recycling/cleanup
    const seenIds = new Set<string>();

    // 3. Render visual nodes
    for (const node of frame.nodes) {
      this.renderVisualNode(node, this.layerContainer, seenIds);
    }

    // 4. Remove unreferenced stale elements
    for (const [id, el] of this.activeElementMap.entries()) {
      if (!seenIds.has(id)) {
        el.remove();
        this.activeElementMap.delete(id);
      }
    }

    // 5. Render or clear unsupported capability diagnostic overlay
    if (this.showDiagnosticsOverlay) {
      this.updateDiagnosticsOverlay(frame);
    }
  }

  /**
   * Calculates aspect-fit scale and positions the stage in the container.
   */
  public updateViewportScale(canvasDimensions: CanvasDimensions): void {
    const containerRect = this.container.getBoundingClientRect
      ? this.container.getBoundingClientRect()
      : { width: 800, height: 450 };

    const cWidth = containerRect.width > 0 ? containerRect.width : 800;
    const cHeight = containerRect.height > 0 ? containerRect.height : 450;

    const scaleX = cWidth / canvasDimensions.width;
    const scaleY = cHeight / canvasDimensions.height;
    const scale = Math.min(scaleX, scaleY);

    this.stageWrapper.style.width = `${canvasDimensions.width}px`;
    this.stageWrapper.style.height = `${canvasDimensions.height}px`;
    this.stageWrapper.style.transform = `scale(${scale})`;
  }

  private renderVisualNode(
    node: VisualNode,
    parentEl: HTMLElement,
    seenIds: Set<string>
  ): void {
    seenIds.add(node.id);

    let el = this.activeElementMap.get(node.id);
    const doc = this.container.ownerDocument;

    if (!el) {
      el = doc.createElement("div");
      el.setAttribute("data-layer-id", node.id);
      el.setAttribute("data-layer-kind", node.kind);
      this.activeElementMap.set(node.id, el);
      parentEl.appendChild(el);
    }

    // Apply computed CSS styles
    for (const [prop, val] of Object.entries(node.computedStyles)) {
      (el.style as any)[prop] = String(val);
    }
    el.style.zIndex = String(node.zIndex);

    // Apply node specific content
    if (node.kind === "text") {
      if (el.textContent !== (node.text ?? "")) {
        el.textContent = node.text ?? "";
      }
    } else if (node.kind === "image") {
      let img = el.querySelector("img") as HTMLImageElement | null;
      if (!img) {
        img = doc.createElement("img");
        img.style.width = "100%";
        img.style.height = "100%";
        img.style.display = "block";
        el.appendChild(img);
      }
      img.style.objectFit = node.objectFit || "contain";
      if (node.assetRef && img.getAttribute("src") !== node.assetRef) {
        img.src = node.assetRef;
      }
    } else if (node.kind === "shape" && node.shapeType === "path" && node.pathData) {
      let svg = el.querySelector("svg");
      if (!svg) {
        svg = doc.createElementNS("http://www.w3.org/2000/svg", "svg") as any;
        svg.style.width = "100%";
        svg.style.height = "100%";
        const path = doc.createElementNS("http://www.w3.org/2000/svg", "path");
        svg.appendChild(path);
        el.appendChild(svg as any);
      }
      const pathEl = svg.querySelector("path");
      if (pathEl) {
        pathEl.setAttribute("d", node.pathData);
        if (node.shapeFill) pathEl.setAttribute("fill", node.shapeFill);
        if (node.shapeStroke) pathEl.setAttribute("stroke", node.shapeStroke);
        if (node.shapeStrokeWidth) pathEl.setAttribute("stroke-width", String(node.shapeStrokeWidth));
      }
    }

    // Recursively render child nodes for groups
    if (node.children && node.children.length > 0) {
      for (const child of node.children) {
        this.renderVisualNode(child, el, seenIds);
      }
    }
  }

  private updateDiagnosticsOverlay(frame: VisualFrame): void {
    const report = frame.unsupportedReport;
    const doc = this.container.ownerDocument;

    if (report && !report.isSupported && report.unsupportedEntities.length > 0) {
      if (!this.diagnosticOverlay) {
        this.diagnosticOverlay = doc.createElement("div");
        this.diagnosticOverlay.className = "cv-unsupported-capability-overlay";
        this.diagnosticOverlay.style.position = "absolute";
        this.diagnosticOverlay.style.top = "12px";
        this.diagnosticOverlay.style.left = "12px";
        this.diagnosticOverlay.style.padding = "8px 14px";
        this.diagnosticOverlay.style.background = "rgba(220, 38, 38, 0.9)";
        this.diagnosticOverlay.style.color = "#FFFFFF";
        this.diagnosticOverlay.style.fontFamily = "monospace";
        this.diagnosticOverlay.style.fontSize = "12px";
        this.diagnosticOverlay.style.borderRadius = "4px";
        this.diagnosticOverlay.style.zIndex = "999999";
        this.diagnosticOverlay.style.pointerEvents = "none";
        this.stageWrapper.appendChild(this.diagnosticOverlay);
      }

      const summary = report.unsupportedEntities
        .map((e) => `[${e.classification}] ${e.entityId}: ${e.reason}`)
        .join("\n");
      this.diagnosticOverlay.textContent = `UNSUPPORTED PREVIEW CAPABILITY:\n${summary}`;
      this.diagnosticOverlay.style.display = "block";
    } else if (this.diagnosticOverlay) {
      this.diagnosticOverlay.style.display = "none";
    }
  }

  public getStageElement(): HTMLElement {
    return this.stageWrapper;
  }

  public destroy(): void {
    this.stageWrapper.remove();
    this.activeElementMap.clear();
  }
}
