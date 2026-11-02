import { test, expect } from '@playwright/test';
import { openStudio, generate, sample, styledPreview } from '../helpers';
import { lutButton, renderResponse, settled, change, cube } from '../export-helpers';

test('guest downloads a valid 33-cube matching the current preview settings', async ({ page }) => {
  await openStudio(page);
  await expect(lutButton(page)).toBeDisabled();
  const initial = renderResponse(page);
  await generate(page);
  await sample(page);
  const body = await settled(page, await initial);
  await styledPreview(page);
  const baseline = await cube(page, body);
  const updated = await change(page, 'warmth', 30);
  expect(updated.body.styleParams).toEqual(body.styleParams);
  expect(await cube(page, updated.body)).not.toEqual(baseline);
});
