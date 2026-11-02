import { test, expect } from '@playwright/test';
import { openStudio, uploadReference, section, success } from '../helpers';
const unsupported = "That file type isn't supported. Please use a JPG, PNG or WebP photo.";
for (const invalid of [
  { name: 'empty.jpg', mimeType: 'image/jpeg', buffer: Buffer.alloc(0), message: 'That file looks empty. Try another photo.' },
  { name: 'unsupported.gif', mimeType: 'image/gif', buffer: Buffer.from('GIF89a'), message: unsupported },
  { name: 'large.jpg', mimeType: 'image/jpeg', buffer: Buffer.alloc(16 * 1024 * 1024), message: 'That photo is 16.0 MB. The limit is 15 MB — try a smaller version.' },
  { name: 'corrupt.jpg', mimeType: 'image/jpeg', buffer: Buffer.from([255, 216, 255, 0]), message: 'Image is corrupt or cannot be decoded.' },
]) {
  test(`${invalid.name}: rejection, replacement and recovery`, async ({ page }) => {
    await openStudio(page);
    // Start valid so client errors also prove a bad replacement discards it.
    await uploadReference(page);
    const ref = section(page, 'Photo you love');
    await expect(ref.getByText('Click or drop to replace')).toBeVisible();
    await uploadReference(page, invalid);
    const button = page.getByRole('button', { name: 'Generate Color Style', exact: true });
    if (invalid.name === 'corrupt.jpg') {
      const rejected = page.waitForResponse(r => r.url().endsWith('/api/generate'));
      await button.click();
      expect((await rejected).status()).toBe(422);
      await expect(page.getByText(success, { exact: true })).toHaveCount(0);
    } else {
      await expect(button).toBeDisabled();
      await expect(ref.locator('img')).toHaveCount(0);
      await expect(ref.getByRole('button', { name: /Add a reference photo/ })).toBeVisible();
    }
    await expect(ref.getByText(invalid.message, { exact: true })).toBeVisible();
    await uploadReference(page);
    await expect(ref.getByText(invalid.message, { exact: true })).toHaveCount(0);
    await expect(ref.getByText('Click or drop to replace')).toBeVisible();
    await expect(ref.locator('img')).toBeVisible();
    await expect(button).toBeEnabled();
    await button.click();
    await expect(page.getByRole('button', { name: 'Generate again', exact: true })).toBeEnabled();
    await expect(page.getByText(success, { exact: true })).toBeVisible();
  });
}
