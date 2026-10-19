import { expect, it, vi, afterEach } from 'vitest';
import { referenceThumbnail } from './thumbnail';
import { loadImage } from './apply-lut';
vi.mock('./apply-lut', () => ({loadImage:vi.fn()}));
afterEach(() => vi.restoreAllMocks());
it('stores only a 256px reference JPEG and permits no thumbnail', async () => {
  expect(await referenceThumbnail(null)).toBe('');
  vi.mocked(loadImage).mockResolvedValue({width:1200,height:800} as HTMLImageElement);
  const drawImage=vi.fn(); const toDataURL=vi.fn().mockReturnValue('data:image/jpeg;base64,thumbnail');
  const canvas={width:0,height:0,getContext:()=>({drawImage}),toDataURL};
  vi.spyOn(document,'createElement').mockReturnValue(canvas as unknown as HTMLCanvasElement);
  expect(await referenceThumbnail('blob:reference')).toBe('data:image/jpeg;base64,thumbnail');
  expect(loadImage).toHaveBeenCalledWith('blob:reference');
  expect(canvas.width).toBe(256);expect(canvas.height).toBe(171);
  expect(toDataURL).toHaveBeenCalledWith('image/jpeg',0.8);
});
