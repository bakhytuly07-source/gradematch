import {
  ServiceError,
  type Adjustments,
  type FileLike,
  type GradeMatchService,
  type Look,
  type LutData,
  type SaveLookInput,
  type StyleParams,
  type User,
} from "./types";

interface ApiLook {
  id: string;
  name: string;
  style_params: StyleParams;
  adjustments: Adjustments;
  thumbnail_url: string;
  is_favorite: boolean;
  created_at: number;
  updated_at: number;
}

export const fromApiLook = (look: ApiLook): Look => ({
  id: look.id,
  name: look.name,
  styleParams: look.style_params,
  adjustments: look.adjustments,
  thumbnail: look.thumbnail_url,
  favorite: look.is_favorite,
  createdAt: look.created_at,
});

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
        error?.message ?? "GradeMatch request failed.",
        ["validation", "auth", "not_found", "unknown"].includes(code) ? code : "unknown",
      );
    }
    return response;
  }

  private async json<T>(path: string, method = "GET", body?: unknown): Promise<T> {
    const init: RequestInit = { method };
    if (body !== undefined) {
      init.headers = { "Content-Type": "application/json" };
      init.body = JSON.stringify(body);
    }
    return (await this.request(path, init)).json();
  }

  private async authenticate(path: string, email: string, password: string): Promise<User> {
    const result = await this.json<{ user: User; access_token: string }>(path, "POST", {
      email,
      password,
    });
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
      if (!(error instanceof ServiceError && error.code === "auth")) throw error;
    } finally {
      this.token = null;
    }
  }

  async getMe(): Promise<User | null> {
    try {
      return await this.json<User>("/auth/me");
    } catch (error) {
      if (error instanceof ServiceError && error.code === "auth") {
        this.token = null;
        return null;
      }
      throw error;
    }
  }

  async generateLook(referenceFile: FileLike): Promise<StyleParams> {
    if (!(referenceFile instanceof Blob))
      throw new ServiceError("Choose an actual image file.", "validation");
    const form = new FormData();
    form.append("referenceFile", referenceFile, referenceFile.name);
    return (await this.request("/generate", { method: "POST", body: form })).json();
  }

  async renderLut(styleParams: StyleParams, adjustments: Adjustments): Promise<LutData> {
    const lut = await this.json<{ size: number; data: number[] }>("/render-lut", "POST", {
      styleParams,
      adjustments,
    });
    return { size: lut.size, data: new Float32Array(lut.data) };
  }

  async saveLook(input: SaveLookInput): Promise<Look> {
    return fromApiLook(await this.json<ApiLook>("/looks", "POST", input));
  }

  async listLooks(): Promise<Look[]> {
    return (await this.json<ApiLook[]>("/looks")).map(fromApiLook);
  }

  async getLook(id: string): Promise<Look> {
    return fromApiLook(await this.json<ApiLook>(`/looks/${encodeURIComponent(id)}`));
  }

  async renameLook(id: string, name: string): Promise<Look> {
    return fromApiLook(
      await this.json<ApiLook>(`/looks/${encodeURIComponent(id)}`, "PATCH", { name }),
    );
  }

  async toggleFavorite(id: string): Promise<Look> {
    return fromApiLook(
      await this.json<ApiLook>(`/looks/${encodeURIComponent(id)}/favorite`, "POST"),
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
