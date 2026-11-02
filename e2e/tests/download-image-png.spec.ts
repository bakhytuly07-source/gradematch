import { test, expect } from '@playwright/test';
import { openStudio, generate, sample, styledPreview } from '../helpers';
import { renderResponse, settled, change } from '../export-helpers';
import { imageDownload } from '../image-export-helpers';

test('guest exports current and warmer Lake previews as decoded PNG images', async ({ page }) => {
  await openStudio(page);
  const button = page.getByRole('button', { name: 'Download image (PNG)', exact: true });
  await expect(button).toBeDisabled();
  const initial = renderResponse(page);
  await generate(page);
  await expect(button).toBeDisabled();
  await sample(page);
  await settled(page, await initial);
  await styledPreview(page);
  await expect(button).toBeEnabled();
  const baseline = await imageDownload(page, 'PNG');
  await change(page, 'warmth', 30);
  const updated = await imageDownload(page, 'PNG');
  expect(updated.hash).not.toBe(baseline.hash);
});
