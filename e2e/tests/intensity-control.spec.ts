import { test, expect } from '@playwright/test';
import { openStudio, generate, sample, styledPreview, pixels } from '../helpers';
import { defaults, renderResponse, settled, settings, change, cube } from '../export-helpers';

test('Look intensity updates preview and LUT and Reset restores the baseline', async ({ page }, info) => {
  await openStudio(page);
  const initial = renderResponse(page);
  await generate(page);
  await sample(page);
  const body = await settled(page, await initial);
  const baseline = await styledPreview(page);
  const original = await cube(page, body);
  await settings(page);
  const changed = await change(page, 'intensity', 20);
  await settings(page, { ...defaults, intensity: 20 });
  const updated = await pixels(page);
  expect(updated[0]).toEqual(baseline[0]);
  expect(updated[1].data).not.toBe(baseline[1].data);
  expect(await cube(page, changed.body)).not.toEqual(original);
  await info.attach('settled-preview-latency', { body: JSON.stringify({ milliseconds: changed.latency, target: 300 }), contentType: 'application/json' });
  const reset = renderResponse(page);
  await page.getByRole('button', { name: 'Reset', exact: true }).click();
  await settled(page, await reset);
  await settings(page);
  expect(await pixels(page)).toEqual(baseline);
  expect(await cube(page, body)).toEqual(original);
});
