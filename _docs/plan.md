# LUT & Color Style Matcher — MVP Scope

**Version:** 2.0 (full-stack: React + FastAPI + SQLite)  
**Product type:** Full-stack web application (React frontend, FastAPI backend, SQLite)  
**Primary audience:** Everyday users and beginners  
**Core goal:** Make it easy to recreate a color style from a reference image and apply it to other photos—without requiring color-grading knowledge.

---

## 1. Product vision

The LUT & Color Style Matcher lets a user upload a reference image they like, estimate its color-grading style, preview the generated look on other photos, make a few simple adjustments, and export either a reusable LUT or a finished image.

The product should feel simple and approachable. Users should not need to understand LUTs, curves, color science, or professional editing workflows.

### Core principle

**Make the first result easy to get, easy to judge, and genuinely useful to export.**

The tool's differentiator is reference-photo style extraction—not a generic collection of presets.

---

## 2. Target audience

**Primary audience:** Everyday users and beginners who want attractive, consistent photo colors without learning professional color grading.

Professional colorists and filmmakers are not the initial target audience.

### UX implications

- Use clear, non-technical labels.
- Keep the upload flow obvious.
- Make the photo preview the main focus.
- Keep adjustments limited and understandable.
- Make exports easy to find.
- Avoid a complicated professional editing workspace.

---

## 3. MVP workflow

1. The user opens the website. No account or login is required to try the tool; an account is needed only to save a look to the Library.
2. The user uploads a reference image.
3. The user clicks **Generate Color Style**.
4. The tool analyzes the reference and creates an estimated color transformation.
5. The user previews the result.
6. The user can upload a separate target photo—or use a sample photo—to test the look.
7. The user compares the original and transformed target image.
8. The user adjusts the look with four simple controls.
9. The user downloads a `.cube` LUT, an edited image, or both.

The reference image is used to estimate the look. A separate target image is used to test whether that look transfers well to another photo.

---

## 4. Input images and file limits

### Decision

Support these formats for the MVP:

- JPEG / JPG
- PNG
- WebP

Use a proposed maximum upload size of **15 MB per image**.

An invalid or cleared reference replacement removes the previous reference and
disables generation. A valid selection clears the error and enables generation.

### Why

These formats cover many images users download from the web or take on their phones. Limiting formats and file size makes browser compatibility and performance easier to manage.

### Alternatives considered

- **HEIC:** Common on Apple devices, but browser support and decoding can vary.
- **RAW:** More complex to decode and interpret; not necessary for the first release.
- **TIFF and other specialist formats:** Useful in some workflows but add scope without serving the core beginner use case.
- **Higher file-size limits:** More demanding on memory and processing time.

### Future possibilities

Add HEIC support and consider RAW support if real user demand justifies the extra work.

---

## 5. Color-style extraction algorithm

### Decision

Start with a deterministic, rule-based color-analysis algorithm. Do not use an AI model in the MVP.

The algorithm should estimate characteristics such as:

- Shadows, midtones, and highlights
- Overall color balance and channel shifts
- Contrast
- Saturation
- Warm/cool tendencies

It will use those measurements to construct a reusable 3D LUT.

### Why

A rule-based approach is easier to implement, debug, benchmark, and run on a plain Python backend. It also avoids AI inference costs and external services.

### Alternatives considered

**Simple color averaging**
- Easier to implement.
- Likely to reproduce scene colors rather than the grading style.
- Too limited to be the primary approach.

**AI-powered extraction**
- Could eventually infer more sophisticated looks.
- Adds model complexity, compute costs, and potentially infrastructure.
- Not necessary before a conventional algorithm has been tested.

**Scene-independent matching**
- The ideal long-term direction is to distinguish grading from lighting, subject colors, and scene content.
- Reliably doing this from one finished reference image is a difficult problem and should not be promised in the MVP.

### Important limitation

A finished reference image shows the result of its original capture and processing—not the original ungraded image or the exact grading settings. The tool can estimate a plausible transformation, but it cannot guarantee recovery of the original grade or a perfect match.

---

## 6. Preview experience

### Decision

Support both:

- A **before/after slider** with a draggable divider.
- A **side-by-side comparison**.

The target photo should be the primary way to judge whether the extracted style is reusable.

### Why

A LUT is useful because it can be applied to other photos. Seeing the transformation on a separate target image demonstrates this more effectively than previewing only the reference.

### Alternatives considered

**Reference-only preview**
- Simpler to build.
- Does not show whether the extracted look works on different scenes.

**Side-by-side only**
- Clear and easy to implement.
- Less interactive than a draggable comparison slider.

**Slider only**
- Space-efficient and intuitive.
- Some users may prefer to see both full images at once.

The MVP will include both comparison modes.

---

## 7. Adjustment controls

### Decision

Include exactly four controls:

| Control | Purpose |
|---|---|
| Look intensity | Controls how strongly the generated style is applied |
| Contrast | Adjusts tonal separation |
| Saturation | Controls color vividness |
| Warmth | Adjusts the warm/cool balance |

Do not include a tint control in the MVP.

### Why

These controls are familiar to beginners and cover several recognizable aspects of a color look without turning the tool into a full editing application.

### Alternatives considered

- RGB curves
- Individual color channels
- HSL controls
- Color wheels
- Separate shadow, midtone, and highlight controls
- Tint / green–magenta adjustment

These can be considered for a future advanced mode.

### Implementation requirement

Adjustments must affect the actual generated transformation and exported LUT—not just the preview. The downloaded LUT and edited image must reflect the selected settings.

---

## 8. LUT export

### Decision

Export a standard **`.cube` 3D LUT**, initially at a resolution of **33 × 33 × 33**.

### Why

The `.cube` format is supported by many professional editing applications, and a 33-point LUT is a practical starting balance between file size and color precision.

### Alternatives considered

- **17 × 17 × 17:** Smaller file, but potentially less precision for complex transformations.
- **65 × 65 × 65:** More samples and potentially higher precision, but larger files and more computation.

### Color-space assumptions

Document the input/output assumptions and target a standard SDR sRGB/Rec.709 workflow initially. Color-space handling must be explicit so the LUT does not behave unpredictably when used in other applications.

### Consistency requirement

The LUT must encode the same transformation used in the browser preview. If the user changes intensity, contrast, saturation, or warmth, the exported LUT must reflect those adjustments.

---

## 9. Edited-image export

### Decision

Allow users to download the finished image in:

- PNG
- JPEG

### Why

Many beginners want the finished photo directly and may not use a separate editing application. The LUT remains the core reusable output, while the edited image makes the tool immediately useful.

### Alternatives considered

**LUT-only export**
- Simpler.
- Less convenient for users who only want a finished photo.

**Image-only export**
- Easy for beginners.
- Loses the ability to reuse the style in other compatible applications.

The MVP will support both LUT and image exports.

---

## 10. Processing, privacy, and performance

### Decision

Split the work between a small Python backend and the browser:

- **Backend (FastAPI):** analyzes the reference image, builds the 33 × 33 × 33 LUT, and applies the four adjustments to it. This is the single source of truth for the color transformation.
- **Browser:** shows the previews, applies the LUT returned by the backend to the target photo (WebGL, with a CPU Web Worker fallback), and renders the comparison UI.

### Single source of truth

The LUT used for the live preview, the exported `.cube`, and the exported edited image is the same data returned by the backend for the same settings. The browser never re-implements the adjustments.

### Privacy

- Uploaded images are processed in memory and are never written to disk or to the database.
- Only a logged-in user who clicks **Save to Library** stores anything: the look's numeric style parameters, its adjustments, and a 256 px JPEG thumbnail of the reference.
- Guests store nothing.

### Limits and targets

- JPEG / PNG / WebP, up to 15 MB, validated on the server by file signature, not only by extension.
- Analysis uses a copy downscaled to at most 1024 px on the longest side.
- **Generate Color Style** finishes in 5 seconds or less for a 15 MB image on a laptop.
- After a control change, the preview updates in 300 ms or less.
- Clear messages for unsupported files, too-large files, and processing failures.

### Alternatives considered

- **Fully in-browser processing:** simpler hosting and maximum privacy, but no server-side library of saved looks.
- **Server-side adjustments only in the export:** the preview could drift from the exported LUT, which breaks the consistency requirement.

### Caveat

Color output can differ slightly between browsers and displays. Cross-browser behavior must be tested.

---

## 11. Technology stack

### Decision

- **Frontend:** TypeScript + React, Vite, Vitest. Canvas / WebGL for applying the LUT in the preview, Web Worker as CPU fallback.
- **Backend:** FastAPI on Python 3.12, `uv` for dependencies, numpy + Pillow + opencv-python-headless for analysis and LUT generation, pytest.
- **Database:** SQLAlchemy 2 ORM + Alembic migrations. SQLite by default, configured through the `DATABASE_URL` environment variable. No SQLite-specific features, so Postgres can replace it later.
- **Auth:** email + password, hashed with bcrypt, bearer tokens.
- **Contract:** `openapi.yaml` in the repository root.

### Build order

1. Frontend with a mock service layer (no backend).
2. `openapi.yaml`, derived from the frontend service layer.
3. Backend with an in-memory store.
4. Backend with SQLite through the ORM.
5. Connect frontend and backend, then test end to end.

### Why

A real backend gives a place for the color engine, accounts, and the Look Library, and the ORM keeps the database replaceable.

---

## 12. Interface design

### Decision

Use a **minimal, beginner-friendly interface**.

The page should prioritize:

- A clear reference-image upload area
- A visible **Generate Color Style** button
- A large image preview
- A clear way to upload a target photo
- Before/after comparison controls
- Four adjustment controls
- Obvious download actions
- A Library page (saved looks) and a simple login / register page, reachable from a small header menu

### Why

The primary audience is beginners. A professional editing workspace with many panels would make the tool look more complicated than it needs to be.

### Alternative considered

A creative workspace with a large preview and a side panel for controls. This could work well later, but the initial interface should prioritize simplicity.

---

## 13. Accounts and user data

### Decision

- **Guests can do everything except save:** upload, generate, preview, adjust, and download LUT / image without an account.
- **Accounts (email + password) exist only for the Look Library.** A logged-in user can save a look, list their looks, open one to apply it to a new target photo, rename it, mark it as favorite, delete it, and download its `.cube` with the saved adjustments.

### Why

Guests keep the zero-friction first experience. The Library gives returning users a reason to register and gives the app persistent data.

### Alternatives considered

- No accounts at all: simplest, but nothing to persist.
- Required accounts before use: adds friction to the first result.

---

## 14. Explicitly out of scope for the MVP

Do not build these in the initial release:

- Video processing
- AI-powered extraction
- A generic preset library (the Library holds only the user's own saved looks)
- Social login, password reset by email, email verification
- Sharing looks by public link
- Advanced manual color-grading controls
- Cloud image storage
- Professional editing-software plugins
- Desktop applications
- RAW and HEIC image support

---

## 15. Biggest technical risk and first milestone

The biggest risk is **whether the generated LUT produces a convincing, reusable color style**. The upload interface and download button are comparatively straightforward.

A valid `.cube` file can still create disappointing results. The extraction algorithm should therefore be tested before investing heavily in the full UI.

### First engineering milestone: proof of concept

1. Implement a basic reference-image analyzer.
2. Generate a 3D LUT from the analysis.
3. Apply the LUT to several different target images.
4. Compare the results against the reference style.
5. Check whether the algorithm simply applies a generic warm tint or contrast increase.
6. Adjust the algorithm based on the results.
7. Benchmark preview and full-resolution processing in the browser.

### Proposed success criterion

The output should visibly evoke the reference's grading style across different target images, rather than merely applying an arbitrary tint or increasing contrast to every image.

This is a qualitative starting criterion. A more formal evaluation set and scoring rubric should be defined after the first prototype exists.

If the proof of concept cannot produce convincing results, improve the algorithm before building the rest of the application.

---

## 16. MVP summary

**Product:** LUT & Color Style Matcher  
**Platform:** Web application  
**Audience:** Everyday users and beginners  
**Accounts:** Optional; needed only to save looks to the Library  
**Processing:** Python backend builds the LUT; browser applies it for live preview  
**Reference input:** JPG, PNG, WebP; proposed 15 MB maximum  
**Generation:** Rule-based analysis; no AI model  
**Preview:** Before/after slider and side-by-side comparison  
**Target image:** Optional separate image or sample image  
**Adjustments:** Look intensity, contrast, saturation, warmth  
**LUT export:** `.cube`, initially 33 × 33 × 33  
**Image export:** PNG and JPEG  
**Out of scope:** Video, AI extraction, generic presets, social login, public sharing, advanced controls, cloud image storage, editor plugins, desktop apps, RAW / HEIC

### Core workflow

**Upload reference → Generate Color Style → Preview on a target → Adjust → Download LUT or edited image.**

### Product principle

Build the smallest complete version that can prove the core idea: a beginner can bring a reference image they love and get a useful, reusable approximation of its color style without needing to understand professional color grading.

---

## 17. Data model (MVP)

- **User:** id, email (unique), password_hash, created_at
- **Look:** id, user_id (foreign key to User), name, style_params (JSON), adjustments (JSON: intensity, contrast, saturation, warmth), thumbnail (256 px JPEG), is_favorite, created_at, updated_at

The API is defined in `openapi.yaml` and derived from the frontend service layer.
