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

import { validateImageFile } from "./validation";
import { fromApiLook, fromApiLooks, fromApiLut, fromApiStyle } from "./mapping";
export { fromApiLook } from "./mapping";

export class ApiService implements GradeMatchService {
  private token: string | null = null;
  private readonly baseUrl: string;

  constructor(baseUrl = "http://localhost:8091") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  private async request(path: string, init: RequestInit = {}): Promise<Response> {
    const headers = new Headers(init.headers);
    if (this.token) headers.set("Authorization", `Bearer ${this.token}`);
    let response: Response;
    try {
      response = await fetch(`${this.baseUrl}/api${path}`, { ...init, headers });
    } catch {
      throw new ServiceError("Could not reach GradeMatch API.", "unknown");
    }
    if (!response.ok) {
      const error = await response.json().catch(() => null);
      const code = error?.code;
      throw new ServiceError(
        typeof error?.message === "string" ? error.message : "GradeMatch request failed. Please try again.",
        response.status < 500 && ["validation", "auth", "not_found", "unknown"].includes(code) ? code : "unknown",
        response.status,
      );
    }
    return response;
  }

  private async json<T>(path: string, method = "GET", body?: unknown, form?: FormData): Promise<T> {
    const init: RequestInit = { method };
    if (form) init.body = form;
    if (body !== undefined) {
      init.headers = { "Content-Type": "application/json" };
      init.body = JSON.stringify(body);
    }
    const response = await this.request(path, init);
    try {
      return await response.json();
    } catch {
      throw new ServiceError("Invalid API response. Please try again.", "unknown");
    }
  }

  private async authenticate(path: string, email: string, password: string): Promise<User> {
    const result = await this.json<{ user: User; access_token: string }>(path, "POST", {
      email,
      password,
    });
    if (!result || typeof result.access_token !== "string" || !result.access_token ||
        typeof result.user?.id !== "string" || typeof result.user?.email !== "string")
      throw new ServiceError("Invalid authentication response. Please try again.", "unknown");
    this.token = result.access_token;
    return result.user;
  }

  register(email: string, password: string) {
    return this.authenticate("/auth/register", email, password);
  }

  login(email: string, password: string) {
    return this.authenticate("/auth/login", email, password);
  }

  async logout(): Promise<void> {
    try {
      await this.request("/auth/logout", { method: "POST" });
    } catch (error) {
      if (!(error instanceof ServiceError && error.status === 401)) throw error;
    } finally {
      this.token = null;
    }
  }

  async getMe(): Promise<User | null> {
    try {
      const user = await this.json<User>("/auth/me");
      if (!user || typeof user.id !== "string" || typeof user.email !== "string")
        throw new ServiceError("Invalid user response. Please try again.", "unknown");
      return user;
    } catch (error) {
      if (error instanceof ServiceError && error.status === 401) {
        this.token = null;
        return null;
      }
      throw error;
    }
  }

  async generateLook(referenceFile: File): Promise<StyleParams> {
    if (!(referenceFile instanceof Blob))
      throw new ServiceError("Choose an actual image file.", "validation");
    const error = validateImageFile(referenceFile);
    if (error) throw new ServiceError(error, "validation");
    const form = new FormData();
    form.append("referenceFile", referenceFile, referenceFile.name);
    return fromApiStyle(await this.json("/generate", "POST", undefined, form));
  }

  async renderLut(styleParams: StyleParams, adjustments: Adjustments): Promise<LutData> {
    const lut = await this.json<{ size: number; data: number[] }>("/render-lut", "POST", {
      styleParams,
      adjustments,
    });
    return fromApiLut(lut);
  }

  async saveLook(input: SaveLookInput): Promise<Look> {
    return fromApiLook(await this.json<unknown>("/looks", "POST", input));
  }

  async listLooks(): Promise<Look[]> {
    return fromApiLooks(await this.json("/looks"));
  }

  async getLook(id: string): Promise<Look> {
    return fromApiLook(await this.json<unknown>(`/looks/${encodeURIComponent(id)}`));
  }

  async renameLook(id: string, name: string): Promise<Look> {
    return fromApiLook(
      await this.json<unknown>(`/looks/${encodeURIComponent(id)}`, "PATCH", { name }),
    );
  }

  async toggleFavorite(id: string): Promise<Look> {
    return fromApiLook(
      await this.json<unknown>(`/looks/${encodeURIComponent(id)}/favorite`, "POST"),
    );
  }

  async deleteLook(id: string): Promise<void> {
    await this.request(`/looks/${encodeURIComponent(id)}`, { method: "DELETE" });
  }

  async downloadLutCube(styleParams: StyleParams, adjustments: Adjustments): Promise<Blob> {
    return (
      await this.request("/download.cube", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ styleParams, adjustments }),
      })
    ).blob();
  }
}
