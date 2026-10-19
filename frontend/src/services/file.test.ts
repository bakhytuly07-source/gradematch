import { afterEach, expect, it, vi } from 'vitest';
import { ApiService } from './api';
import { MockService } from './mock';
import { MAX_FILE_BYTES } from './validation';
afterEach(() => vi.unstubAllGlobals());
it('sends actual File bytes/name without forcing a multipart header', async () => {
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({id: 's', shadowTint: [0,0,0], highlightTint: [1,1,1], baseSaturation: 1})));
  vi.stubGlobal('fetch', fetch);
  const file = new File([new Uint8Array([1, 2, 3, 4])], 'reference.png', {type: 'image/png'});
  await new ApiService(undefined, null).generateLook(file);
  const init = fetch.mock.calls[0]![1];
  const upload = init.body.get('referenceFile') as File;
  expect(upload.name).toBe('reference.png');
  expect(init.headers.has('Content-Type')).toBe(false);
  const bytes = await new Promise<ArrayBuffer>((resolve) => {const r = new FileReader(); r.onload = () => resolve(r.result as ArrayBuffer); r.readAsArrayBuffer(upload);});
  expect(new Uint8Array(bytes)).toEqual(new Uint8Array([1,2,3,4]));
});
it('both implementations validate real files including inclusive 15MiB boundary', async () => {
  vi.stubGlobal('fetch', vi.fn().mockImplementation(async () => new Response(JSON.stringify({id:'s', shadowTint:[0,0,0], highlightTint:[1,1,1], baseSaturation:1}))));
  for (const api of [new ApiService(undefined, null), new MockService(() => 0)]) {
    for (const file of [new File([], 'empty.jpg', {type:'image/jpeg'}), new File(['x'], 'bad.gif', {type:'image/gif'}), new File([new Uint8Array(MAX_FILE_BYTES+1)], 'large.jpg', {type:'image/jpeg'})])
      await expect(api.generateLook(file)).rejects.toMatchObject({code:'validation'});
    await expect(api.generateLook(new File([new Uint8Array(MAX_FILE_BYTES)], 'limit.jpg', {type:'image/jpeg'}))).resolves.toHaveProperty('id');
  }
});
