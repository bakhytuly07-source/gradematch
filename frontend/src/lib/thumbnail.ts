import { loadImage } from './apply-lut';

/** Store only a 256px JPEG copy of the reference, never the target/original. */
export async function referenceThumbnail(source: string | null): Promise<string> {
  if (!source) return '';
  const image = await loadImage(source);
  const scale = 256 / Math.max(image.width, image.height);
  const canvas = document.createElement('canvas');
  canvas.width = Math.max(1, Math.round(image.width * scale));
  canvas.height = Math.max(1, Math.round(image.height * scale));
  canvas.getContext('2d')!.drawImage(image, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL('image/jpeg', 0.8);
}
