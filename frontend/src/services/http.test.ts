import { afterEach, expect, it, vi } from 'vitest';
import { ApiService } from './api';
import { DEFAULT_ADJUSTMENTS } from './types';
const style = { id: 's', shadowTint: [0, 0, 0] as [number, number, number], highlightTint: [1, 1, 1] as [number, number, number], baseSaturation: 1 };
const look = { id: 'a/b', name: 'L', style_params: style, adjustments: DEFAULT_ADJUSTMENTS, thumbnail_url: '', is_favorite: false, created_at: 1700000000000, updated_at: 1700000000000 };
const json = (data: unknown, status=200) => new Response(JSON.stringify(data), {status});
afterEach(() => vi.unstubAllGlobals());
it('routes all Library operations and never parses 204 or retries mutations', async () => {
  const fetch = vi.fn().mockResolvedValueOnce(json(look, 201)).mockResolvedValueOnce(json([look]))
    .mockResolvedValueOnce(json(look)).mockResolvedValueOnce(json(look)).mockResolvedValueOnce(json(look))
    .mockResolvedValueOnce(new Response(null, {status: 204}));
  vi.stubGlobal('fetch', fetch);
  const api = new ApiService('https://api.example/');
  await api.saveLook({name: 'L', thumbnail: '', styleParams: style, adjustments: DEFAULT_ADJUSTMENTS});
  await api.listLooks(); await api.getLook('a/b'); await api.renameLook('a/b', 'New'); await api.toggleFavorite('a/b'); await api.deleteLook('a/b');
  expect(fetch.mock.calls.map(([url, init]) => [url, init.method])).toEqual([
    ['https://api.example/api/looks', 'POST'], ['https://api.example/api/looks', 'GET'],
    ['https://api.example/api/looks/a%2Fb', 'GET'], ['https://api.example/api/looks/a%2Fb', 'PATCH'],
    ['https://api.example/api/looks/a%2Fb/favorite', 'POST'], ['https://api.example/api/looks/a%2Fb', 'DELETE'],
  ]);
});
it('only maps getMe HTTP 401 to signed out; errors remain recoverable ServiceErrors', async () => {
  const fetch = vi.fn().mockResolvedValueOnce(json({code: 'auth', message: 'server'}, 500))
    .mockResolvedValueOnce(new Response('bad json')).mockRejectedValueOnce(new TypeError('offline'))
    .mockResolvedValueOnce(json({code: 'not_found', message: 'Missing'}, 404))
    .mockResolvedValueOnce(json({code: 'validation', message: 'Bad'}, 422));
  vi.stubGlobal('fetch', fetch);
  const api = new ApiService();
  await expect(api.getMe()).rejects.toMatchObject({code: 'unknown', status: 500});
  await expect(api.getMe()).rejects.toMatchObject({code: 'unknown'});
  await expect(api.listLooks()).rejects.toMatchObject({code: 'unknown'});
  await expect(api.getLook('x')).rejects.toMatchObject({code: 'not_found'});
  await expect(api.renameLook('x', '')).rejects.toMatchObject({code: 'validation'});
  expect(fetch).toHaveBeenCalledTimes(5);
});
