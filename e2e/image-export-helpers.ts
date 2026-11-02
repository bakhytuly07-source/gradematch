import { expect, type Page } from '@playwright/test';
import { preview } from './helpers';
import { download } from './export-helpers';

export async function imageDownload(page: Page, format: 'PNG' | 'JPEG') {
  const file = await download(page, `Download image (${format})`);
  if (format === 'PNG') {
    expect(file.filename).toMatch(/\.png$/);
    expect([...file.bytes.subarray(0, 8)]).toEqual([137, 80, 78, 71, 13, 10, 26, 10]);
  } else {
    expect(file.filename).toMatch(/\.jpe?g$/);
    expect([...file.bytes.subarray(0, 3)]).toEqual([255, 216, 255]);
  }
  const comparison = await preview(page).locator('canvas').evaluateAll(async (nodes, src) => {
    // Chromium's real decoder validates the downloaded bytes; a detached canvas
    // compares every decoded RGB channel with both visible preview canvases.
    const image = new Image(); image.src = src; await image.decode();
    const c = document.createElement('canvas');
    c.width = image.naturalWidth; c.height = image.naturalHeight;
    c.getContext('2d')!.drawImage(image, 0, 0);
    const decoded = c.getContext('2d')!.getImageData(0, 0, c.width, c.height).data;
    const differences = nodes.map(node => {
      const canvas = node as HTMLCanvasElement;
      if (canvas.width !== c.width || canvas.height !== c.height) throw new Error('Export/preview dimensions differ');
      const expected = canvas.getContext('2d')!.getImageData(0, 0, c.width, c.height).data;
      let total = 0, count = 0;
      const histogram = new Array(256).fill(0);
      for (let i = 0; i < decoded.length; i++) if (i % 4 !== 3) {
        const delta = Math.abs(decoded[i] - expected[i]);
        total += delta; count++; histogram[delta]++;
      }
      let cumulative = 0, p99 = 0;
      for (; p99 < 255; p99++) { cumulative += histogram[p99]; if (cumulative >= count * 0.99) break; }
      return { mean: total / count, max: histogram.findLastIndex(n => n > 0), p99 };
    });
    const digest = await crypto.subtle.digest('SHA-256', decoded);
    return { width: c.width, height: c.height, differences,
      hash: Array.from(new Uint8Array(digest)).map(v => v.toString(16).padStart(2, '0')).join('') };
  }, `data:image/${format === 'PNG' ? 'png' : 'jpeg'};base64,${file.bytes.toString('base64')}`);
  // The fixed Lake target is 1280x864, below the 1600px preview cap:
  // PNG therefore allows zero channel error (no preview resampling).
  // JPEG quality .92 allows mean RGB error <=3 and 99th percentile <=15
  // on the 0..255 scale for chroma subsampling and lossy compression.
  expect({ width: comparison.width, height: comparison.height }).toEqual({ width: 1280, height: 864 });
  const [before, after] = comparison.differences;
  if (format === 'PNG') expect(after.max).toBe(0);
  else { expect(after.mean).toBeLessThanOrEqual(3); expect(after.p99).toBeLessThanOrEqual(15); }
  expect(before.mean).toBeGreaterThan(3);
  expect(before.mean).toBeGreaterThan(after.mean);
  console.log(`${format} decoded ${comparison.width}x${comparison.height}: preview mean RGB error ${after.mean.toFixed(3)}, p99 ${after.p99}; original mean error ${before.mean.toFixed(3)}`);
  return comparison;
}
