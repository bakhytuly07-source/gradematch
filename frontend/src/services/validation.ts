import type { FileLike } from "./types";

export const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"];
export const MAX_FILE_BYTES = 15 * 1024 * 1024;

/** Returns a friendly error message, or null when the file is OK. */
export function validateImageFile(file: FileLike | null | undefined): string | null {
  if (!file) return "Please choose a photo.";
  if (!ACCEPTED_TYPES.includes(file.type)) {
    return "That file type isn't supported. Please use a JPG, PNG or WebP photo.";
  }
  if (file.size === 0) return "That file looks empty. Try another photo.";
  if (file.size > MAX_FILE_BYTES) {
    const mb = (file.size / 1024 / 1024).toFixed(1);
    return `That photo is ${mb} MB. The limit is 15 MB — try a smaller version.`;
  }
  return null;
}

export function validateEmail(email: string): string | null {
  if (!email.trim()) return "Enter your email.";
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) return "That email doesn't look right.";
  return null;
}

export function validatePassword(pw: string): string | null {
  if (!pw) return "Enter a password.";
  if (pw.length < 8) return "Password needs at least 8 characters.";
  return null;
}
