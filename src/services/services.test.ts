import { describe, expect, it } from "vitest";
import { MockService, buildLut, lutToCube } from "./mock";
import { DEFAULT_ADJUSTMENTS } from "./types";
import { validateImageFile, MAX_FILE_BYTES } from "./validation";

const jpg = { name: "a.jpg", type: "image/jpeg", size: 1000 };
const svc = () => new MockService(() => 0);

describe("upload validation", () => {
  it("accepts JPG, PNG and WebP", () => {
    for (const type of ["image/jpeg", "image/png", "image/webp"]) {
      expect(validateImageFile({ name: "x", type, size: 10 })).toBeNull();
    }
  });
  it("rejects other types", () => {
    expect(validateImageFile({ name: "x.gif", type: "image/gif", size: 10 })).toMatch(/JPG, PNG or WebP/);
  });
  it("allows exactly 15 MB and rejects more", () => {
    expect(validateImageFile({ ...jpg, size: MAX_FILE_BYTES })).toBeNull();
    expect(validateImageFile({ ...jpg, size: MAX_FILE_BYTES + 1 })).toMatch(/15 MB/);
  });
  it("rejects missing file", () => {
    expect(validateImageFile(null)).not.toBeNull();
  });
});

describe("MockService", () => {
  it("generateLook validates the file", async () => {
    await expect(svc().generateLook({ ...jpg, type: "application/pdf" })).rejects.toThrow();
    await expect(svc().generateLook(jpg)).resolves.toHaveProperty("id");
  });

  it("renderLut returns a 33x33x33 LUT", async () => {
    const s = svc();
    const lut = await s.renderLut(await s.generateLook(jpg), DEFAULT_ADJUSTMENTS);
    expect(lut.size).toBe(33);
    expect(lut.data.length).toBe(33 * 33 * 33 * 3);
  });

  it("zero intensity and neutral sliders give an identity LUT", async () => {
    const s = svc();
    const style = await s.generateLook(jpg);
    const lut = buildLut(style, { intensity: 0, contrast: 0, saturation: 0, warmth: 0 });
    const last = lut.data.length - 3;
    expect(lut.data[last]!).toBeCloseTo(1);
    expect(lut.data[3]!).toBeCloseTo(1 / 32);
  });

  it("warmth raises red and lowers blue", async () => {
    const s = svc();
    const style = await s.generateLook(jpg);
    const n = { intensity: 0, contrast: 0, saturation: 0, warmth: 0 };
    const mid = ((16 * 33 + 16) * 33 + 16) * 3;
    const a = buildLut(style, n).data;
    const b = buildLut(style, { ...n, warmth: 50 }).data;
    expect(b[mid]!).toBeGreaterThan(a[mid]!);
    expect(b[mid + 2]!).toBeLessThan(a[mid + 2]!);
  });

  it("cube file has header and 35937 rows", async () => {
    const s = svc();
    const text = lutToCube(await s.renderLut(await s.generateLook(jpg), DEFAULT_ADJUSTMENTS));
    expect(text).toContain("LUT_3D_SIZE 33");
    expect(text.trim().split("\n").length).toBe(4 + 35937);
  });

  it("auth: register, logout, login, wrong password", async () => {
    const s = svc();
    await expect(s.register("bad", "12345678")).rejects.toThrow();
    await expect(s.register("a@b.co", "short")).rejects.toThrow();
    await s.register("a@b.co", "password1");
    expect(await s.getMe()).not.toBeNull();
    await s.logout();
    expect(await s.getMe()).toBeNull();
    await expect(s.login("a@b.co", "nope")).rejects.toThrow();
    await s.login("A@b.co", "password1");
    expect((await s.getMe())?.email).toBe("a@b.co");
  });

  it("looks require login and are private per user", async () => {
    const s = svc();
    const style = await s.generateLook(jpg);
    const input = { name: "Warm", thumbnail: "", styleParams: style, adjustments: DEFAULT_ADJUSTMENTS };
    await expect(s.saveLook(input)).rejects.toThrow(/log in/);
    await s.register("a@b.co", "password1");
    const look = await s.saveLook(input);
    expect((await s.renameLook(look.id, "Golden")).name).toBe("Golden");
    expect((await s.toggleFavorite(look.id)).favorite).toBe(true);
    await s.logout();
    await s.register("c@d.co", "password1");
    expect(await s.listLooks()).toHaveLength(0);
    await expect(s.getLook(look.id)).rejects.toThrow();
    await s.logout();
    await s.login("a@b.co", "password1");
    await s.deleteLook(look.id);
    expect(await s.listLooks()).toHaveLength(0);
  });
});
