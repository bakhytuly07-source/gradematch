import { expect, type Page } from '@playwright/test';
import path from 'node:path';
export const reference = path.resolve('backend/evaluation/reference-neutral.jpg');
export const success = 'Color style ready. Now pick a photo to apply it to.';
export const section = (page: Page, title: string) => page.locator('section').filter({ has: page.getByRole('heading', { name: new RegExp('^\\d+ ' + title + '$') }) });
export async function openStudio(page: Page) {
  const restored = page.waitForResponse(r => r.url().endsWith('/api/auth/me'));
  await page.goto('/');
  await restored;
  await expect(page.getByRole('button', { name: 'Generate Color Style', exact: true })).toBeDisabled();
}
export async function uploadReference(page: Page, file: any = reference) {
  // The file input is hidden and unnamed; scope it to the accessible section.
  await section(page, 'Photo you love').locator('input[type=file]').setInputFiles(file);
}
export async function generate(page: Page) {
  await uploadReference(page);
  const response = page.waitForResponse(r => r.url().endsWith('/api/generate'));
  await page.getByRole('button', { name: 'Generate Color Style', exact: true }).click();
  expect((await response).status()).toBe(200);
  await expect(page.getByText(success, { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Download LUT (.cube)', exact: true })).toBeEnabled();
}
export async function exportsReady(page: Page) {
  for (const format of ['PNG', 'JPEG']) await expect(page.getByRole('button', { name: `Download image (${format})`, exact: true })).toBeEnabled();
}
export async function sample(page: Page, name = 'Lake') {
  await page.getByRole('button').filter({ has: page.getByRole('img', { name: `${name} sample`, exact: true }) }).click();
  await exportsReady(page);
}
export const preview = (page: Page) => page.locator('section').filter({ has: page.getByRole('button', { name: 'Before / after', exact: true }) });
export async function pixels(page: Page) {
  return preview(page).locator('canvas').evaluateAll(nodes => nodes.map(node => {
    const c = node as HTMLCanvasElement;
    return { width: c.width, height: c.height, data: Array.from(c.getContext('2d')!.getImageData(0, 0, c.width, c.height).data) };
  }));
}
export async function styledPreview(page: Page) {
  await expect(preview(page).getByText('Before', { exact: true })).toBeVisible();
  await expect(preview(page).getByText('After', { exact: true })).toBeVisible();
  await expect.poll(async () => {
    const cs = await pixels(page);
    return cs.length === 2 && cs.every(c => c.width > 0 && c.height > 0 && c.data.some((v, i) => i % 4 !== 3 && v > 0)) && cs[0].data.some((v, i) => i % 4 !== 3 && Math.abs(v - cs[1].data[i]) > 2);
  }).toBe(true);
  return pixels(page);
}
export async function sourcePixels(page: Page, src: string) {
  return page.evaluate(async src => {
    const img = new Image(); img.src = src; await img.decode();
    const c = document.createElement('canvas');
    const scale = Math.min(1, 1600 / Math.max(img.naturalWidth, img.naturalHeight));
    c.width = Math.round(img.naturalWidth * scale); c.height = Math.round(img.naturalHeight * scale);
    c.getContext('2d')!.drawImage(img, 0, 0, c.width, c.height);
    return { width: c.width, height: c.height, data: Array.from(c.getContext('2d')!.getImageData(0, 0, c.width, c.height).data) };
  }, src);
}
export async function dragDivider(page: Page, percent: number) {
  const divider = page.getByRole('slider', { name: 'Before and after divider', exact: true });
  const box = await preview(page).locator('canvas').first().boundingBox();
  if (!box) throw new Error('No preview bounds');
  const start = Number(await divider.inputValue());
  await page.mouse.move(box.x + box.width * start / 100, box.y + box.height / 2);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * percent / 100, box.y + box.height / 2, { steps: 10 });
  await page.mouse.up();
  // Pointer coordinates round to CSS pixels; allow one percentage point.
  await expect.poll(async () => Math.abs(Number(await divider.inputValue()) - percent)).toBeLessThanOrEqual(1);
  const geometry = await divider.evaluate(input => {
    const parent = input.parentElement!;
    const line = Array.from(parent.children).find(el => el instanceof HTMLElement && el.style.left.endsWith('%')) as HTMLElement;
    const after = parent.querySelectorAll('canvas')[1];
    const r = parent.getBoundingClientRect();
    return { percent: (line.getBoundingClientRect().x - r.x) / r.width * 100, clip: after.style.clipPath };
  });
  expect(Math.abs(geometry.percent - percent)).toBeLessThanOrEqual(1);
  expect(Math.abs(parseFloat(geometry.clip.split(' ').at(-1)!) - percent)).toBeLessThanOrEqual(1);
  return box;
}
