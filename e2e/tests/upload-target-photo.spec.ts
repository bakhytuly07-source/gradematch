import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import { openStudio, generate, section, styledPreview, exportsReady, sourcePixels, expectedStyled, observeLut } from '../helpers';
test('PNG target, JPG replacement and unsupported target recovery', async ({ page }) => {
  await openStudio(page);
  const currentLut = observeLut(page);
  await generate(page);
  const input = section(page, 'Your photo').locator('input[type=file]');
  let previous: any;
  for (const [filename, mime, width, height] of [['target.png', 'image/png', 96, 64], ['replacement.jpg', 'image/jpeg', 80, 120]] as const) {
    const file = `e2e/fixtures/${filename}`;
    await input.setInputFiles(file);
    await exportsReady(page);
    const src = `data:${mime};base64,${fs.readFileSync(file).toString('base64')}`;
    const expectedBefore = await sourcePixels(page, src);
    await expect.poll(async () => (await styledPreview(page))[0]).toEqual(expectedBefore);
    const [before, after] = await styledPreview(page);
    expect({ width: before.width, height: before.height }).toEqual({ width, height });
    expect(after).toEqual(await expectedStyled(page, src, await currentLut()));
    if (previous) expect(before).not.toEqual(previous);
    previous = before;
  }
  const message = "That file type isn't supported. Please use a JPG, PNG or WebP photo.";
  await input.setInputFiles({ name: 'bad.gif', mimeType: 'image/gif', buffer: Buffer.from('GIF89a') });
  await expect(section(page, 'Your photo').getByText(message, { exact: true })).toBeVisible();
  await input.setInputFiles('e2e/fixtures/target.png');
  await expect(section(page, 'Your photo').getByText(message, { exact: true })).toHaveCount(0);
  const expected = await sourcePixels(page, `data:image/png;base64,${fs.readFileSync('e2e/fixtures/target.png').toString('base64')}`);
  await expect.poll(async () => (await styledPreview(page))[0]).toEqual(expected);
  await exportsReady(page);
});
