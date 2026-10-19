import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiService } from "./api";
import { DEFAULT_ADJUSTMENTS, type StyleParams } from "./types";

const style: StyleParams = {
  id: "s",
  shadowTint: [0.4, 0.5, 0.6],
  highlightTint: [0.6, 0.5, 0.4],
  baseSaturation: 1,
};
const apiLook = {
  id: "l",
  name: "Look",
  style_params: style,
  adjustments: DEFAULT_ADJUSTMENTS,
  thumbnail_url: "",
  is_favorite: true,
  created_at: 1700000000000,
  updated_at: 1700000000010,
};
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });

afterEach(() => vi.unstubAllGlobals());

describe("ApiService", () => {
  it("retains bearer token and maps Look fields without renaming nested settings", async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(json({ user: { id: "u", email: "a@b.co" }, access_token: "secret" }))
      .mockResolvedValueOnce(json(apiLook, 201));
    vi.stubGlobal("fetch", fetch);
    const api = new ApiService();
    expect(await api.login("a@b.co", "password")).toEqual({ id: "u", email: "a@b.co" });
    const input = {
      name: "Look",
      thumbnail: "",
      styleParams: style,
      adjustments: DEFAULT_ADJUSTMENTS,
    };
    expect(await api.saveLook(input)).toEqual({
      id: "l",
      name: "Look",
      styleParams: style,
      adjustments: DEFAULT_ADJUSTMENTS,
      thumbnail: "",
      favorite: true,
      createdAt: 1700000000000,
    });
    const [, init] = fetch.mock.calls[1]!;
    expect(init.headers.get("Authorization")).toBe("Bearer secret");
    expect(JSON.parse(init.body)).toEqual(input);
  });

  it("maps getMe 401 to null, handles empty logout, and returns float32 LUT and Blob", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(json({ code: "auth", message: "Expired" }, 401))
        .mockResolvedValueOnce(new Response(null, { status: 204 }))
        .mockResolvedValueOnce(json({ size: 33, data: [0.1, 0.2, 0.3] }))
        .mockResolvedValueOnce(new Response("LUT_3D_SIZE 33")),
    );
    const api = new ApiService();
    expect(await api.getMe()).toBeNull();
    await expect(api.logout()).resolves.toBeUndefined();
    const lut = await api.renderLut(style, DEFAULT_ADJUSTMENTS);
    expect(lut.data).toBeInstanceOf(Float32Array);
    expect((await api.downloadLutCube(style, DEFAULT_ADJUSTMENTS)).size).toBeGreaterThan(0);
  });

  it("uploads actual bytes and rejects metadata-only files", async () => {
    const fetch = vi.fn().mockResolvedValue(json(style));
    vi.stubGlobal("fetch", fetch);
    const api = new ApiService();
    const file = new File(["bytes"], "sample.png", { type: "image/png" });
    expect(await api.generateLook(file)).toEqual(style);
    expect(fetch.mock.calls[0]![1].body.get("referenceFile").size).toBe(5);
    await expect(api.generateLook({ name: "x", type: "image/png", size: 5 })).rejects.toMatchObject(
      { code: "validation" },
    );
  });
});
