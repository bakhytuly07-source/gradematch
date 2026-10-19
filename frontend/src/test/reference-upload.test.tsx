import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import type { ComponentType } from 'react';
import { MockService } from '@/services/mock';
import { MAX_FILE_BYTES, validateImageFile } from '@/services/validation';
const state = vi.hoisted(() => ({ generate: vi.fn() }));
vi.mock('@/services', async () => ({ ...(await vi.importActual('@/services')), useMe: () => null, service: { generateLook: state.generate } }));
vi.mock('@/hooks/use-rendered-lut', () => ({ useRenderedLut: () => ({ result: null, ready: false, error: null }) }));
vi.mock('@tanstack/react-router', async () => ({ ...(await vi.importActual('@tanstack/react-router')), useNavigate: () => vi.fn() }));
import { Route } from '@/routes/index';
const Studio = Route.options.component as ComponentType;
const file = (type: string, size = 1) => new File([new Uint8Array(size)], 'reference.jpg', { type });
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });
it.each(['image/jpeg', 'image/png', 'image/webp'])('accepts %s through the inclusive limit in metadata and mock', async type => {
  const mock = new MockService(() => 0);
  for (const size of [1, MAX_FILE_BYTES]) {
    const reference = file(type, size);
    expect(validateImageFile(reference)).toBeNull();
    await expect(mock.generateLook(reference)).resolves.toHaveProperty('id');
  }
});
it.each([
  [file('image/jpeg', 0), 'empty'], [file('image/gif'), "isn't supported"], [file('image/jpeg', MAX_FILE_BYTES + 1), '15 MB'],
])('rejects invalid metadata before mock generation', async (reference, message) => {
  expect(validateImageFile(reference)).toContain(message);
  await expect(new MockService(() => 0).generateLook(reference)).rejects.toMatchObject({ code: 'validation', message: expect.stringContaining(message) });
});
it('blocks invalid selections after a valid reference and recovers via picker/drop', async () => {
  vi.stubGlobal('ResizeObserver', class { observe() {} unobserve() {} disconnect() {} });
  vi.spyOn(Route, 'useSearch').mockReturnValue({});
  vi.stubGlobal('URL', { createObjectURL: () => 'blob:reference' });
  state.generate.mockResolvedValue({ id: 's', shadowTint: [0,0,0], highlightTint: [1,1,1], baseSaturation: 1 });
  render(<Studio />);
  const zone = screen.getByRole('button', { name: /Add a reference photo/ });
  const input = zone.querySelector('input')!;
  const button = screen.getByRole('button', { name: 'Generate Color Style' });
  expect(button).toBeDisabled();
  const select = (reference: File) => fireEvent.change(input, { target: { files: [reference] } });
  select(file('image/jpeg'));
  expect(button).toBeEnabled();
  for (const reference of [file('image/jpeg', 0), file('image/gif'), file('image/png', MAX_FILE_BYTES + 1)]) {
    select(reference);
    expect(button).toBeDisabled();
    fireEvent.click(button);
    expect(state.generate).not.toHaveBeenCalled();
    expect(zone.querySelector('img')).toBeNull();
    fireEvent.drop(zone, { dataTransfer: { files: [file('image/webp')] } });
    expect(screen.queryByText(/looks empty|isn't supported|The limit is 15 MB/)).toBeNull();
    expect(button).toBeEnabled();
  }
  fireEvent.click(button);
  await waitFor(() => expect(state.generate).toHaveBeenCalledTimes(1));
  await screen.findByRole('button', { name: 'Generate again' });
});
