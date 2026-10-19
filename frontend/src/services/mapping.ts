import { ServiceError, type Look, type LutData, type StyleParams, type Adjustments } from './types';
import { z } from 'zod';

const channel = z.number().finite().min(0).max(1);
export const styleSchema = z.object({
  id: z.string(), shadowTint: z.tuple([channel, channel, channel]),
  highlightTint: z.tuple([channel, channel, channel]), baseSaturation: z.number().finite(),
});
const adjustmentsSchema = z.object({intensity: z.number().min(0).max(100),
  contrast: z.number().min(-50).max(50), saturation: z.number().min(-50).max(50), warmth: z.number().min(-50).max(50)});
const timestamp = z.number().int().nonnegative().max(Number.MAX_SAFE_INTEGER);
const lookSchema = z.object({id: z.string(), name: z.string(), style_params: styleSchema,
  adjustments: adjustmentsSchema, thumbnail_url: z.string(), is_favorite: z.boolean(),
  created_at: timestamp, updated_at: timestamp});

export function parseResponse<T>(schema: z.ZodType<T>, value: unknown): T {
  const parsed = schema.safeParse(value);
  if (!parsed.success) throw new ServiceError('Invalid API response. Please try again.', 'unknown');
  return parsed.data;
}
export function fromApiStyle(value: unknown): StyleParams { return parseResponse(styleSchema, value); }
export function fromApiLook(value: unknown): Look {
  const look = parseResponse(lookSchema, value);
  // updated_at is required/validated but not retained: UI orders by creation time.
  return {id: look.id, name: look.name, styleParams: look.style_params,
    adjustments: look.adjustments, thumbnail: look.thumbnail_url, favorite: look.is_favorite,
    createdAt: look.created_at};
}
export function fromApiLooks(value: unknown): Look[] {
  if (!Array.isArray(value)) throw new ServiceError('Invalid Library response. Please try again.', 'unknown');
  return value.map(fromApiLook);
}
export function fromApiLut(value: unknown): LutData {
  const lut = parseResponse(z.object({size: z.literal(33), data: z.array(channel).length(107811)}), value);
  return {size: lut.size, data: new Float32Array(lut.data)};
}
