import { expect, type Page, type Response } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { section, pixels, expectedStyled, exportsReady } from './helpers';

export const defaults = { intensity: 80, contrast: 0, saturation: 0, warmth: 0 };
export const labels = { intensity: 'Look intensity', contrast: 'Contrast', saturation: 'Saturation', warmth: 'Warmth' };
export const lutButton = (page: Page) => page.getByRole('button', { name: 'Download LUT (.cube)', exact: true });
export const renderResponse = (page: Page, adjustments = defaults) => page.waitForResponse(r =>
  r.url().endsWith('/api/render-lut') && JSON.stringify(r.request().postDataJSON().adjustments) === JSON.stringify(adjustments));

export async function settings(page: Page, values = defaults) {
  const fine = section(page, 'Fine-tune');
  for (const key of Object.keys(labels) as (keyof typeof labels)[]) {
    const slider = fine.getByRole('slider', { name: labels[key], exact: true });
    await expect(slider).toHaveAttribute('aria-valuenow', String(values[key]));
    // Scope the displayed number to the wrapper containing this named slider.
    await expect(fine.locator('div.space-y-3').filter({ has: page.getByRole('slider', { name: labels[key], exact: true }) }).getByText(String(values[key]), { exact: true })).toBeVisible();
  }
}
export async function settled(page: Page, response: Response) {
  expect(response.status()).toBe(200);
  const lut = await response.json();
  const src = await page.getByRole('img', { name: 'Lake sample', exact: true }).getAttribute('src');
  const expected = await expectedStyled(page, src!, lut);
  await expect.poll(async () => (await pixels(page))[1]?.data, { intervals: [10, 20, 50] }).toBe(expected.data);
  await exportsReady(page);
  return response.request().postDataJSON();
}
export async function change(page: Page, key: keyof typeof labels, value: number) {
  const slider = section(page, 'Fine-tune').getByRole('slider', { name: labels[key], exact: true });
  const current = Number(await slider.getAttribute('aria-valuenow'));
  // Real keyboard input, with the last key defining the latency measurement.
  const direction = value < current ? 'ArrowLeft' : 'ArrowRight';
  for (let i = 1; i < Math.abs(value - current); i++) await slider.press(direction);
  const response = renderResponse(page, { ...defaults, [key]: value });
  const start = performance.now();
  await slider.press(direction);
  const body = await settled(page, await response);
  const latency = performance.now() - start;
  console.log(`${labels[key]} settled preview: ${latency.toFixed(1)} ms; product target 300 ms (${latency <= 300 ? 'within' : 'above'} target)`);
  return { body, latency };
}
export async function download(page: Page, name: string) {
  const pending = page.waitForEvent('download');
  await page.getByRole('button', { name, exact: true }).click();
  const file = await pending;
  expect(await file.failure()).toBeNull();
  return { filename: file.suggestedFilename(), bytes: await readFile((await file.path())!) };
}
export async function cube(page: Page, previewBody: unknown) {
  const response = page.waitForResponse(r => r.url().endsWith('/api/download.cube'));
  const file = await download(page, 'Download LUT (.cube)');
  const exported = await response;
  expect(exported.status()).toBe(200);
  expect(exported.request().postDataJSON()).toEqual(previewBody);
  expect(file.filename).toMatch(/\.cube$/);
  const text = file.bytes.toString('utf8');
  expect(text).toMatch(/^LUT_3D_SIZE 33\s*$/m);
  const rows = text.split(/\r?\n/).map(line => line.split('#')[0].trim()).filter(line => /^[+\-.\d]/.test(line)).map(line => line.split(/\s+/).map(Number));
  expect(rows).toHaveLength(35937);
  expect(rows.every(row => row.length === 3 && row.every(Number.isFinite))).toBe(true);
  return rows;
}
