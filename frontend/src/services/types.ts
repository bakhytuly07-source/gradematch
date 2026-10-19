export interface User {
  id: string;
  email: string;
}

/** The color style pulled from a reference photo. Opaque to the UI. */
export interface StyleParams {
  id: string;
  /** Tint applied to shadows / highlights, each channel 0..1 */
  shadowTint: [number, number, number];
  highlightTint: [number, number, number];
  /** Base saturation multiplier of the look */
  baseSaturation: number;
}

export interface Adjustments {
  /** 0..100 */
  intensity: number;
  /** -50..50 */
  contrast: number;
  /** -50..50 */
  saturation: number;
  /** -50..50 */
  warmth: number;
}

export const DEFAULT_ADJUSTMENTS: Adjustments = {
  intensity: 80,
  contrast: 0,
  saturation: 0,
  warmth: 0,
};

export interface LutData {
  size: number;
  /** size^3 * 3 floats in 0..1, red changes fastest (cube file order) */
  data: Float32Array;
}

export interface Look {
  id: string;
  name: string;
  favorite: boolean;
  thumbnail: string;
  styleParams: StyleParams;
  adjustments: Adjustments;
  createdAt: number;
}

export interface SaveLookInput {
  name: string;
  thumbnail: string;
  styleParams: StyleParams;
  adjustments: Adjustments;
}

export interface FileLike {
  name: string;
  type: string;
  size: number;
}

export class ServiceError extends Error {
  constructor(
    message: string,
    public code: "validation" | "auth" | "not_found" | "unknown" = "unknown",
    public status?: number,
  ) {
    super(message);
  }
}

export interface GradeMatchService {
  register(email: string, password: string): Promise<User>;
  login(email: string, password: string): Promise<User>;
  logout(): Promise<void>;
  getMe(): Promise<User | null>;
  generateLook(referenceFile: File): Promise<StyleParams>;
  renderLut(styleParams: StyleParams, adjustments: Adjustments): Promise<LutData>;
  saveLook(input: SaveLookInput): Promise<Look>;
  listLooks(): Promise<Look[]>;
  getLook(id: string): Promise<Look>;
  renameLook(id: string, name: string): Promise<Look>;
  toggleFavorite(id: string): Promise<Look>;
  deleteLook(id: string): Promise<void>;
  downloadLutCube(styleParams: StyleParams, adjustments: Adjustments): Promise<Blob>;
}
