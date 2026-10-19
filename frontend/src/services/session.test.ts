import { afterEach, expect, it, vi } from 'vitest';
import { ApiService } from './api';
import { MockService } from './mock';
import { createSessionService } from './session';
const user = {id:'u', email:'a@b.co'};
const json = (data: unknown, status=200) => new Response(JSON.stringify(data), {status});
afterEach(() => {vi.unstubAllGlobals(); sessionStorage.clear();});
it('restores a stored token on a new adapter and clears expired sessions', async () => {
  const fetch = vi.fn().mockResolvedValueOnce(json({user, access_token:'secret', token_type:'bearer'}))
    .mockResolvedValueOnce(json(user)).mockResolvedValueOnce(json({code:'auth',message:'Expired'},401));
  vi.stubGlobal('fetch', fetch);
  await new ApiService().register(user.email,'password123');
  const reload = new ApiService();
  expect(await reload.getMe()).toEqual(user);
  expect(new Headers(fetch.mock.calls[1]![1].headers).get('Authorization')).toBe('Bearer secret');
  expect(await reload.getMe()).toBeNull();
  expect(sessionStorage.length).toBe(0);
});
it.each([204,401,500,'offline'])('clears local credentials and auth notifications on logout %s', async status => {
  const fetch = vi.fn().mockResolvedValueOnce(json({user,access_token:'secret',token_type:'bearer'}));
  if (status === 'offline') fetch.mockRejectedValueOnce(new Error('offline'));
  else fetch.mockResolvedValueOnce(status === 204 ? new Response(null,{status:204}) : json({code:status===401?'auth':'unknown',message:'failed'},status as number));
  fetch.mockResolvedValueOnce(json({code:'auth',message:'No token'},401));
  vi.stubGlobal('fetch',fetch);
  const session = createSessionService(new ApiService());
  const listener = vi.fn(); session.subscribe(listener);
  await session.service.login(user.email,'password123');
  await session.service.logout().catch(() => {});
  expect(listener).toHaveBeenLastCalledWith(null);
  expect(sessionStorage.length).toBe(0);
  expect(await new ApiService().getMe()).toBeNull();
  expect(new Headers(fetch.mock.calls[2]![1].headers).has('Authorization')).toBe(false);
});
it('does not let stale getMe restoration repopulate a logged-out UI', async () => {
  const base = new MockService(() => 0);
  let resolve!: (value: typeof user) => void;
  vi.spyOn(base,'getMe').mockReturnValue(new Promise(r => {resolve = r;}));
  const session = createSessionService(base); const listener = vi.fn(); session.subscribe(listener);
  const pending = session.service.getMe();
  await session.service.logout(); resolve(user);
  expect(await pending).toBeNull(); expect(listener).toHaveBeenLastCalledWith(null);
});
