import { expect, it, vi, afterEach } from 'vitest';
import { fromApiLook, fromApiLut } from './mapping';
import { ApiService } from './api';
import { DEFAULT_ADJUSTMENTS } from './types';
const style = {id: 's', shadowTint: [0.1, 0.2, 0.3] as [number, number, number], highlightTint: [0.4, 0.5, 0.6] as [number, number, number], baseSaturation: 1.25};
const raw = {id: 'l', name: 'Look', style_params: style, adjustments: {...DEFAULT_ADJUSTMENTS, warmth: -1.5}, thumbnail_url: '', is_favorite: false, created_at: 1700000000123, updated_at: 1700000000456};
afterEach(() => vi.unstubAllGlobals());
it('validates every required Look field and maps independent numeric models', () => {
  const before = JSON.stringify(raw);
  const result = fromApiLook(raw);
  expect(result).toEqual({id: 'l', name: 'Look', styleParams: style, adjustments: raw.adjustments, thumbnail: '', favorite: false, createdAt: raw.created_at});
  result.styleParams.shadowTint[0] = 0.9;
  expect(JSON.stringify(raw)).toBe(before);
  for (const key of Object.keys(raw)) {
    const incomplete = {...raw}; delete (incomplete as Record<string, unknown>)[key];
    expect(() => fromApiLook(incomplete)).toThrow(/Invalid/);
  }
  expect(() => fromApiLook({...raw, updated_at: '2026-01-01'})).toThrow();
});
it('preserves LUT sample ordering and rejects wrong size/count/nonfinite samples', () => {
  const data = Array.from({length: 107811}, (_, i) => i / 107811);
  expect(fromApiLut({size: 33, data}).data).toEqual(new Float32Array(data));
  for (const invalid of [{size: 32, data}, {size: 33, data: data.slice(1)}, {size: 33, data: [...data.slice(1), NaN]}])
    expect(() => fromApiLut(invalid)).toThrow(/Invalid/);
});
it('maps every Look operation and preserves exact outbound camelCase keys', async () => {
  const fetch = vi.fn().mockImplementation(async (url: string, init: RequestInit) =>
    new Response(JSON.stringify(url.endsWith('/looks') && init.method === 'GET' ? [raw] : raw)));
  vi.stubGlobal('fetch', fetch);
  const api = new ApiService();
  const input = {name: 'Look', thumbnail: '', styleParams: style, adjustments: raw.adjustments};
  const expected = fromApiLook(raw);
  expect(await api.saveLook(input)).toEqual(expected);
  expect(JSON.parse(fetch.mock.calls[0]![1].body as string)).toEqual(input);
  expect(await api.listLooks()).toEqual([expected]);
  expect(await api.getLook('l')).toEqual(expected);
  expect(await api.renameLook('l', 'Look')).toEqual(expected);
  expect(await api.toggleFavorite('l')).toEqual(expected);
});
