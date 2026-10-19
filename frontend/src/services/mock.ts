import {
  ServiceError,
  type Adjustments,
  type GradeMatchService,
  type Look,
  type LutData,
  type SaveLookInput,
  type StyleParams,
  type User,
} from "./types";
import { validateEmail, validateImageFile, validatePassword } from "./validation";

export const LUT_SIZE = 33;

const clamp = (v: number) => (v < 0 ? 0 : v > 1 ? 1 : v);

/** Pure LUT builder used by the mock backend. */
export function buildLut(style: StyleParams, adj: Adjustments, size = LUT_SIZE): LutData {
  const data = new Float32Array(size * size * size * 3);
  const k = adj.intensity / 100;
  const contrast = 1 + adj.contrast / 50; // 0..2
  const sat = style.baseSaturation * (1 + adj.saturation / 50) * k + (1 - k) * (1 + adj.saturation / 50);
  const warm = adj.warmth / 50; // -1..1
  let i = 0;
  for (let b = 0; b < size; b++) {
    for (let g = 0; g < size; g++) {
      for (let r = 0; r < size; r++) {
        let R = r / (size - 1);
        let G = g / (size - 1);
        let B = b / (size - 1);
        const l = 0.2126 * R + 0.7152 * G + 0.0722 * B;
        // split tone, blended by intensity
        const sh = (1 - l) * 0.25 * k;
        const hi = l * 0.25 * k;
        R += (style.shadowTint[0] - 0.5) * sh + (style.highlightTint[0] - 0.5) * hi;
        G += (style.shadowTint[1] - 0.5) * sh + (style.highlightTint[1] - 0.5) * hi;
        B += (style.shadowTint[2] - 0.5) * sh + (style.highlightTint[2] - 0.5) * hi;
        // saturation
        const l2 = 0.2126 * R + 0.7152 * G + 0.0722 * B;
        R = l2 + (R - l2) * sat;
        G = l2 + (G - l2) * sat;
        B = l2 + (B - l2) * sat;
        // contrast
        R = (R - 0.5) * contrast + 0.5;
        G = (G - 0.5) * contrast + 0.5;
        B = (B - 0.5) * contrast + 0.5;
        // warmth
        R += warm * 0.08;
        B -= warm * 0.08;
        data[i++] = clamp(R);
        data[i++] = clamp(G);
        data[i++] = clamp(B);
      }
    }
  }
  return { size, data };
}

export function lutToCube(lut: LutData, title = "GradeMatch Look"): string {
  const lines = [`TITLE "${title}"`, `LUT_3D_SIZE ${lut.size}`, "DOMAIN_MIN 0.0 0.0 0.0", "DOMAIN_MAX 1.0 1.0 1.0"];
  for (let i = 0; i < lut.data.length; i += 3) {
    lines.push(`${lut.data[i]!.toFixed(6)} ${lut.data[i + 1]!.toFixed(6)} ${lut.data[i + 2]!.toFixed(6)}`);
  }
  return lines.join("\n") + "\n";
}

const uid = () => Math.random().toString(36).slice(2, 10);

export class MockService implements GradeMatchService {
  private users = new Map<string, { user: User; password: string }>();
  private looks = new Map<string, Look & { ownerId: string }>();
  private current: User | null = null;

  constructor(private latency: () => number = () => 1000 + Math.random() * 1000) {}

  private wait() {
    const ms = this.latency();
    return ms > 0 ? new Promise((r) => setTimeout(r, ms)) : Promise.resolve();
  }

  private requireUser(): User {
    if (!this.current) throw new ServiceError("Please log in first.", "auth");
    return this.current;
  }

  private ownLook(id: string) {
    const u = this.requireUser();
    const look = this.looks.get(id);
    if (!look || look.ownerId !== u.id) throw new ServiceError("That look wasn't found.", "not_found");
    return look;
  }

  private strip(l: Look & { ownerId: string }): Look {
    const { ownerId: _o, ...rest } = l;
    return { ...rest };
  }

  async register(email: string, password: string) {
    await this.wait();
    const e = validateEmail(email) ?? validatePassword(password);
    if (e) throw new ServiceError(e, "validation");
    const key = email.trim().toLowerCase();
    if (this.users.has(key)) throw new ServiceError("An account with this email already exists.", "validation");
    const user = { id: uid(), email: key };
    this.users.set(key, { user, password });
    this.current = user;
    return user;
  }

  async login(email: string, password: string) {
    await this.wait();
    const rec = this.users.get(email.trim().toLowerCase());
    if (!rec || rec.password !== password) throw new ServiceError("Email or password is incorrect.", "auth");
    this.current = rec.user;
    return rec.user;
  }

  async logout() {
    this.current = null;
  }

  async getMe() {
    return this.current;
  }

  async generateLook(file: File): Promise<StyleParams> {
    const err = validateImageFile(file);
    if (err) throw new ServiceError(err, "validation");
    await this.wait();
    // Simple warm look, slightly varied per file
    const v = (file.size % 100) / 1000;
    return {
      id: uid(),
      shadowTint: [0.45, 0.5 + v, 0.62],
      highlightTint: [0.75, 0.6, 0.4 - v],
      baseSaturation: 1.1,
    };
  }

  async renderLut(style: StyleParams, adj: Adjustments) {
    return buildLut(style, adj);
  }

  async saveLook(input: SaveLookInput) {
    const u = this.requireUser();
    await this.wait();
    const name = input.name.trim() || "Untitled look";
    const look = { ...input, name, id: uid(), favorite: false, createdAt: Date.now(), ownerId: u.id };
    this.looks.set(look.id, look);
    return this.strip(look);
  }

  async listLooks() {
    const u = this.requireUser();
    await this.wait();
    return [...this.looks.values()]
      .filter((l) => l.ownerId === u.id)
      .sort((a, b) => b.createdAt - a.createdAt)
      .map((l) => this.strip(l));
  }

  async getLook(id: string) {
    return this.strip(this.ownLook(id));
  }

  async renameLook(id: string, name: string) {
    const l = this.ownLook(id);
    if (!name.trim()) throw new ServiceError("Name can't be empty.", "validation");
    l.name = name.trim();
    return this.strip(l);
  }

  async toggleFavorite(id: string) {
    const l = this.ownLook(id);
    l.favorite = !l.favorite;
    return this.strip(l);
  }

  async deleteLook(id: string) {
    this.ownLook(id);
    this.looks.delete(id);
  }

  async downloadLutCube(style: StyleParams, adj: Adjustments) {
    const lut = await this.renderLut(style, adj);
    return new Blob([lutToCube(lut)], { type: "text/plain" });
  }
}
