import { expect, type Page } from '@playwright/test';
import { randomUUID } from 'node:crypto';
import { section } from './helpers';

export const uniqueName = (prefix: string) => `${prefix} ${randomUUID()}`;
export const card = (page: Page, name: string) => page.getByRole('article').filter({ has: page.getByRole('img', { name, exact: true }) });
export async function register(page: Page) {
  const restored = page.waitForResponse(r => r.url().endsWith('/api/auth/me'));
  await page.goto('/register');
  await restored;
  await page.getByLabel('Email', { exact: true }).fill(`e2e-${randomUUID()}@example.com`);
  await page.getByLabel('Password', { exact: true }).fill('password123');
  await page.getByRole('button', { name: 'Create account', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Your looks', exact: true })).toBeVisible();
  await expect(page.getByText('No saved looks yet.', { exact: true })).toBeVisible();
}
export async function save(page: Page, name: string) {
  await page.getByRole('button', { name: '☆ Save to Library', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByRole('heading', { name: 'Name this look', exact: true })).toBeVisible();
  await dialog.getByPlaceholder('e.g. Golden hour').fill(name);
  const response = page.waitForResponse(r => r.url().endsWith('/api/looks') && r.request().method() === 'POST');
  await dialog.getByRole('button', { name: 'Save', exact: true }).click();
  expect((await response).status()).toBe(201);
  const saved = await (await response).json();
  await expect(page.getByText('Saved to your library.', { exact: true }).last()).toBeVisible();
  await expect(dialog).toHaveCount(0);
  return saved;
}
export async function thumbnail(page: Page, name: string) {
  const article = card(page, name);
  await expect(article).toBeVisible();
  await expect.poll(() => article.getByRole('img', { name, exact: true }).evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth > 0 && img.naturalHeight > 0)).toBe(true);
  return article;
}
export const controls = ['Look intensity', 'Contrast', 'Saturation', 'Warmth'];
export async function values(page: Page, expected: number[]) {
  for (const [i, name] of controls.entries()) {
    const slider = section(page, 'Fine-tune').getByRole('slider', { name, exact: true });
    await expect(slider).toHaveAttribute('aria-valuenow', String(expected[i]));
    await expect(section(page, 'Fine-tune').locator('div.space-y-3').filter({ has: page.getByRole('slider', { name, exact: true }) }).getByText(String(expected[i]), { exact: true })).toBeVisible();
  }
}
export async function adjust(page: Page, expected: number[]) {
  for (const [i, name] of controls.entries()) {
    const slider = section(page, 'Fine-tune').getByRole('slider', { name, exact: true });
    const current = Number(await slider.getAttribute('aria-valuenow'));
    if (current === expected[i]) continue;
    const response = page.waitForResponse(r => r.url().endsWith('/api/render-lut') && r.request().postDataJSON().adjustments[['intensity', 'contrast', 'saturation', 'warmth'][i]] === expected[i]);
    await slider.press(`${expected[i] < current ? 'ArrowLeft' : 'ArrowRight'}`, { noWaitAfter: true });
    for (let j = 1; j < Math.abs(expected[i] - current); j++) await slider.press(expected[i] < current ? 'ArrowLeft' : 'ArrowRight');
    expect((await response).status()).toBe(200);
    await expect(page.getByRole('button', { name: 'Download LUT (.cube)', exact: true })).toBeEnabled();
  }
  await values(page, expected);
}
export async function openLook(page: Page, name: string, expected: number[]) {
  await card(page, name).getByRole('link', { name: 'Open', exact: true }).click();
  await expect(page.getByText(`"${name}" loaded — pick a photo to apply it to.`, { exact: true })).toBeVisible();
  await values(page, expected);
  await expect(page.getByRole('button', { name: 'Download LUT (.cube)', exact: true })).toBeEnabled();
}
