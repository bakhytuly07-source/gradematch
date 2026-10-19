import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import type { ComponentType } from 'react';
import { DEFAULT_ADJUSTMENTS, type Look, type User } from '@/services/types';
const state = vi.hoisted(() => ({ me: {id:'a',email:'a@b.co'} as User | null | undefined, look: 'private', getLook: vi.fn(), generate: vi.fn(), navigate: vi.fn() }));
vi.mock('@/services', async () => ({ ...(await vi.importActual('@/services')), useMe: () => state.me, service: {getLook:state.getLook,generateLook:state.generate} }));
vi.mock('@/hooks/use-rendered-lut', () => ({useRenderedLut: () => ({result:null,ready:false,error:null})}));
vi.mock('@tanstack/react-router', async () => ({...(await vi.importActual('@tanstack/react-router')), useNavigate: () => state.navigate}));
import { Route } from '@/routes/index';
const Studio = Route.options.component as ComponentType;
const privateLook: Look = {id:'private',name:'A private look',favorite:false,thumbnail:'data:image/jpeg;base64,private',createdAt:1,styleParams:{id:'private-style',shadowTint:[0,0,0],highlightTint:[1,1,1],baseSaturation:1},adjustments:{intensity:91,contrast:21,saturation:31,warmth:41}};
function mount() {
  vi.spyOn(Route,'useSearch').mockImplementation(() => ({look:state.look || undefined}));
  vi.stubGlobal('ResizeObserver',class {observe() {} unobserve() {} disconnect() {}});
  return render(<Studio/>);
}
const warmth = () => screen.getByRole('slider',{name:'Warmth'}).getAttribute('aria-valuenow');
afterEach(() => {cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); state.me={id:'a',email:'a@b.co'};state.look='private';state.getLook.mockReset();});
it('drops private saved settings/thumbnail when switching accounts while Studio is unmounted', async () => {
  state.getLook.mockResolvedValue(privateLook);
  const first=mount(); await waitFor(() => expect(warmth()).toBe('41'));
  first.unmount(); state.me={id:'b',email:'b@b.co'};state.look='';
  mount();
  expect(warmth()).toBe(String(DEFAULT_ADJUSTMENTS.warmth));
  expect(screen.queryByText('Preview')).toBeNull();
  expect(document.querySelector('img[src="data:image/jpeg;base64,private"]')).toBeNull();
});
it('clears mounted private settings on logout and account switch', async () => {
  state.getLook.mockResolvedValue(privateLook);
  const view=mount(); await waitFor(() => expect(warmth()).toBe('41'));
  state.look=''; state.me=null;view.rerender(<Studio/>);
  expect(warmth()).toBe('0');
  state.me={id:'b',email:'b@b.co'};view.rerender(<Studio/>);
  expect(warmth()).toBe('0');
});
it('ignores a pending private look response after switching accounts', async () => {
  let resolve!: (look:Look) => void;
  state.getLook.mockReturnValue(new Promise<Look>(r => {resolve=r;}));
  const view=mount();
  state.look='';state.me={id:'b',email:'b@b.co'};view.rerender(<Studio/>);
  await act(async () => {resolve(privateLook);});
  expect(warmth()).toBe('0');
  expect(screen.queryByText('Preview')).toBeNull();
});

it('restores the same owner draft after auth restoration, without rendering it while unresolved', async () => {
  state.getLook.mockResolvedValue(privateLook);
  const first=mount(); await waitFor(() => expect(warmth()).toBe('41'));
  first.unmount();state.look='';state.me=undefined;
  const next=mount();expect(warmth()).toBe('0');
  state.me={id:'a',email:'a@b.co'};next.rerender(<Studio/>);
  expect(warmth()).toBe('41');
});
it('keeps a generated guest draft through sign-in for the save workflow', async () => {
  state.me=null;state.look='';
  vi.stubGlobal('URL',{createObjectURL: () => 'blob:guest-reference'});
  state.generate.mockResolvedValue(privateLook.styleParams);
  const view=mount();
  const zone=screen.getByRole('button',{name:/Add a reference photo/});
  fireEvent.change(zone.querySelector('input')!,{target:{files:[new File(['bytes'],'guest.jpg',{type:'image/jpeg'})]}});
  fireEvent.click(screen.getByRole('button',{name:'Generate Color Style'}));
  await screen.findByText('Preview');
  state.me={id:'b',email:'b@b.co'};view.rerender(<Studio/>);
  expect(screen.getByText('Preview')).toBeTruthy();
  expect(document.querySelector('img[src="blob:guest-reference"]')).toBeTruthy();
});
