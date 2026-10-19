import type { LutData } from "@/services";

/** Applies a 3D LUT (trilinear) to RGBA pixels in place. */
export function applyLutToPixels(px: Uint8ClampedArray, lut: LutData) {
  const n = lut.size;
  const d = lut.data;
  const m = n - 1;
  const s = m / 255;
  for (let i = 0; i < px.length; i += 4) {
    const r = px[i]! * s, g = px[i + 1]! * s, b = px[i + 2]! * s;
    const r0 = Math.min(r | 0, m - 1), g0 = Math.min(g | 0, m - 1), b0 = Math.min(b | 0, m - 1);
    const fr = r - r0, fg = g - g0, fb = b - b0;
    for (let c = 0; c < 3; c++) {
      const at = (rr: number, gg: number, bb: number) => d[((bb * n + gg) * n + rr) * 3 + c]!;
      const c00 = at(r0, g0, b0) * (1 - fr) + at(r0 + 1, g0, b0) * fr;
      const c10 = at(r0, g0 + 1, b0) * (1 - fr) + at(r0 + 1, g0 + 1, b0) * fr;
      const c01 = at(r0, g0, b0 + 1) * (1 - fr) + at(r0 + 1, g0, b0 + 1) * fr;
      const c11 = at(r0, g0 + 1, b0 + 1) * (1 - fr) + at(r0 + 1, g0 + 1, b0 + 1) * fr;
      const c0 = c00 * (1 - fg) + c10 * fg;
      const c1 = c01 * (1 - fg) + c11 * fg;
      px[i + c] = (c0 * (1 - fb) + c1 * fb) * 255;
    }
  }
}

export function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((res, rej) => {
    const img = new Image();
    img.onload = () => res(img);
    img.onerror = () => rej(new Error("Couldn't read that photo."));
    img.src = src;
  });
}

/** Draws img (scaled to maxSide) into a new canvas, optionally graded. */
export function renderToCanvas(img: HTMLImageElement, lut: LutData | null, maxSide = 1600) {
  const scale = Math.min(1, maxSide / Math.max(img.naturalWidth, img.naturalHeight));
  const w = Math.round(img.naturalWidth * scale), h = Math.round(img.naturalHeight * scale);
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d")!;
  ctx.drawImage(img, 0, 0, w, h);
  if (lut) {
    const data = ctx.getImageData(0, 0, w, h);
    applyLutToPixels(data.data, lut);
    ctx.putImageData(data, 0, 0);
  }
  return canvas;
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
