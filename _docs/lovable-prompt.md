# Lovable / Claude Design prompt: GradeMatch frontend

Paste the prompt below into Lovable (or Claude Design). Save the generated project to GitHub, then move it into `frontend/`.

```
Build a web app called GradeMatch. A beginner uploads a reference photo they love,
the app extracts its color style, the user previews that style on another photo,
adjusts four sliders, and downloads a .cube LUT or the edited image.

PAGES
1. Studio (home, no login needed):
   - Step 1: reference upload (drag and drop, JPG/PNG/WebP, max 15 MB, clear error messages)
   - Button "Generate Color Style" (disabled until a reference is chosen, shows progress)
   - Step 2: target photo upload, or choose one of 3 bundled sample photos
   - Large preview with two modes: draggable before/after slider and side-by-side
   - Four sliders: Look intensity, Contrast, Saturation, Warmth (reset button)
   - Downloads: "Download LUT (.cube)", "Download image (PNG)", "Download image (JPEG)"
   - "Save to Library" button (asks to log in if not logged in)
2. Library (login required): grid of saved looks (thumbnail, name, favorite star),
   open a look to apply it to a new target photo, rename, favorite, delete, download .cube
3. Login / Register: email + password, clear validation errors

DESIGN DIRECTION (not generic SaaS)
- Feels like a photographer's light table: near-black neutral background so photos
  stay the hero, the preview takes at least 60% of the screen
- One warm accent color (amber), no purple gradients, no glassmorphism, no stock illustrations
- Large friendly type, one display font plus one clean sans, generous spacing
- Plain-language labels, no color-science jargon
- Inspiration (mood only): Halide, Darkroom, VSCO, Linear's calm dark UI
- Mobile friendly: sliders and preview work on a phone

ARCHITECTURE (important)
- Put EVERY backend call in one services layer: src/services/ with an interface
  GradeMatchService and a MockService implementation. UI components never call fetch directly.
- Interface methods: register, login, logout, getMe, generateLook(referenceFile),
  renderLut(styleParams, adjustments) -> 33x33x33 LUT data, saveLook, listLooks,
  getLook, renameLook, toggleFavorite, deleteLook, downloadLutCube(styleParams, adjustments)
- MockService keeps everything in memory, simulates 1-2 s latency, returns a simple
  warm-tinted LUT, and validates file type and size like the real backend will
- The preview applies the LUT returned by renderLut (never re-implement adjustments in the UI);
  debounce slider changes by 150 ms
- Add Vitest tests for the services layer and the upload validation
```
