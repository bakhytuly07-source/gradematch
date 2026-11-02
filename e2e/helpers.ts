import { expect, type Page } from '@playwright/test';
import path from 'node:path';
export const reference = path.resolve('e2e/fixtures/reference-warm.jpg');
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
// Hash every pixel to compare full-size samples without transferring millions
// of numbers through the browser protocol. Samples also quantify color change.
const summarize = async (c: HTMLCanvasElement) => {
  const bytes = c.getContext('2d')!.getImageData(0, 0, c.width, c.height).data;
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  const samples = Array.from({ length: 192 }, (_, i) => bytes[Math.floor(i / 3 * bytes.length / 64 / 4) * 4 + i % 3]);
  return { width: c.width, height: c.height,
    data: Array.from(new Uint8Array(digest)).map(v => v.toString(16).padStart(2, '0')).join(''),
    nonempty: bytes.some((v, i) => i % 4 !== 3 && v > 0), samples };
};
export async function pixels(page: Page) {
  return preview(page).locator('canvas').evaluateAll(async (nodes, code) => {
    const summarize = new Function('return (' + code + ')')();
    return Promise.all(nodes.map(c => summarize(c)));
  }, summarize.toString());
}
export async function styledPreview(page: Page) {
  await expect(preview(page).getByText('Before', { exact: true })).toBeVisible();
  await expect(preview(page).getByText('After', { exact: true })).toBeVisible();
  await expect.poll(async () => {
    const cs = await pixels(page);
    return cs.length === 2 && cs.every(c => c.width > 0 && c.height > 0 && c.nonempty) && cs[0].samples.some((v: number, i: number) => Math.abs(v - cs[1].samples[i]) > 2);
  }).toBe(true);
  return pixels(page);
}
export async function sourcePixels(page: Page, src: string) {
  return page.evaluate(async ({src, code}) => {
    const img = new Image(); img.src = src; await img.decode();
    const c = document.createElement('canvas');
    const scale = Math.min(1, 1600 / Math.max(img.naturalWidth, img.naturalHeight));
    c.width = Math.round(img.naturalWidth * scale); c.height = Math.round(img.naturalHeight * scale);
    c.getContext('2d')!.drawImage(img, 0, 0, c.width, c.height);
    return new Function('return (' + code + ')')()(c);
  }, {src, code: summarize.toString()});
}
export async function dragDivider(page: Page, percent: number) {
  const divider = page.getByRole('slider', { name: 'Before and after divider', exact: true });
  const box = await preview(page).locator('canvas').first().boundingBox();
  if (!box) throw new Error('No preview bounds');
  const start = Number(await divider.inputValue());
  await page.mouse.move(box.x + box.width * start / 100, box.y + box.height / 2);
  await page.mouse.down();
  const edgeOffset = percent === 0 ? -10 : percent === 100 ? 10 : 0;
  await page.mouse.move(box.x + box.width * percent / 100 + edgeOffset, box.y + box.height / 2, { steps: 10 });
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
// Same production renderer and actual backend LUT, used only to calculate
// expected pixels in a detached canvas (as in the legacy guest parity check).
export async function expectedStyled(page: Page, src: string, lut: any) {
  const fs = await import('node:fs');
  const ts = await import('../frontend/node_modules/typescript/lib/typescript.js');
  const renderer = ts.transpileModule(fs.readFileSync('frontend/src/lib/apply-lut.ts', 'utf8'), {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 },
  }).outputText.replaceAll('export ', '');
  return page.evaluate(async ({ renderer, src, lut, code }) => {
    const { loadImage, renderToCanvas } = new Function(renderer + ';return {loadImage,renderToCanvas}')();
    lut.data = new Float32Array(lut.data);
    const c = renderToCanvas(await loadImage(src), lut);
    return new Function('return (' + code + ')')()(c);
  }, { renderer, src, lut, code: summarize.toString() });
}
export function observeLut(page: Page) {
  let latest: any;
  page.on('response', async r => { if (r.url().endsWith('/api/render-lut') && r.ok()) latest = await r.json(); });
  return async () => { await expect.poll(() => !!latest).toBe(true); return latest; };
}
export async function fullImages(page: Page, expected: Awaited<ReturnType<typeof pixels>>) {
  const figures = preview(page).getByRole('figure');
  await expect(figures).toHaveCount(2);
  for (const [i, caption] of ['Before', 'After'].entries()) {
    await expect(figures.nth(i).getByText(caption, { exact: true })).toBeVisible();
    const canvas = figures.nth(i).locator('canvas');
    const rendering = await canvas.evaluate(c => {
      const r = c.getBoundingClientRect(), style = getComputedStyle(c);
      return { width: r.width, height: r.height, clip: style.clipPath, objectFit: style.objectFit };
    });
    expect(rendering.clip).toBe('none');
    expect(rendering.objectFit).not.toBe('cover');
    expect(Math.abs(rendering.width / rendering.height - expected[i].width / expected[i].height)).toBeLessThan(0.01);
  }
  expect(await pixels(page)).toEqual(expected);
  const left = await figures.nth(0).boundingBox(), right = await figures.nth(1).boundingBox();
  expect(left!.x + left!.width).toBeLessThanOrEqual(right!.x);
  expect(Math.abs(left!.y - right!.y)).toBeLessThan(2);
}

// UUIDs keep UI-created accounts distinct across runs, retries, and workers.
export async function openRegistration(page: Page) {
  await openStudio(page);
  await page.getByRole('banner').getByRole('link', { name: 'Log in', exact: true }).click();
  await page.getByRole('link', { name: 'Create an account', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Create your account', exact: true })).toBeVisible();
}
export async function registerAccount(page: Page, email: string, password: string) {
  await openRegistration(page);
  await page.getByLabel('Email', { exact: true }).fill(email);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Create account', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Your looks', exact: true })).toBeVisible();
  await expect(page.getByRole('banner').getByRole('button', { name: 'Log out', exact: true })).toBeVisible();
}
