# Service contract audit (#13)

Sources: [GradeMatchService](../frontend/src/services/types.ts),
[MockService](../frontend/src/services/mock.ts), [OpenAPI 3.1](../openapi.yaml).
Each method maps to exactly one operationId of the same name. Routes include `/api`.
`Bearer` means `security: [{bearerAuth: []}]`; `Guest` means explicit `security: []`.
All listed errors carry JSON `Error {code, message}`; error bodies are never null.

| Method / operationId | HTTP | Route | Request | Success response | Errors | Security |
| --- | --- | --- | --- | --- | --- | --- |
| register | POST | /api/auth/register | JSON RegisterInput | 201 JSON AuthResult | 409, 422, 500 | Guest |
| login | POST | /api/auth/login | JSON LoginInput | 200 JSON AuthResult | 401, 422, 500 | Guest |
| logout | POST | /api/auth/logout | None | 204 empty | 401, 500 | Bearer |
| getMe | GET | /api/auth/me | None | 200 JSON User | 401, 500 | Bearer |
| generateLook | POST | /api/generate | multipart GenerateInput | 200 JSON StyleParams | 413, 415, 422, 500 | Guest |
| renderLut | POST | /api/render-lut | JSON LutSettings | 200 JSON LutData | 422, 500 | Guest |
| saveLook | POST | /api/looks | JSON SaveLookInput | 201 JSON Look | 401, 422, 500 | Bearer |
| listLooks | GET | /api/looks | None | 200 JSON Look[] | 401, 500 | Bearer |
| getLook | GET | /api/looks/{id} | Path id; no body | 200 JSON Look | 401, 404, 500 | Bearer |
| renameLook | PATCH | /api/looks/{id} | Path id + JSON RenameLookInput | 200 JSON Look | 401, 404, 422, 500 | Bearer |
| toggleFavorite | POST | /api/looks/{id}/favorite | Path id; no body | 200 JSON Look | 401, 404, 500 | Bearer |
| deleteLook | DELETE | /api/looks/{id} | Path id; no body | 204 empty | 401, 404, 500 | Bearer |
| downloadLutCube | POST | /api/download.cube | JSON LutSettings | 200 text/plain string → Blob | 422, 500 | Guest |

## Required fields and absent bodies

All bodies above are required; an absent required field fails with 422 (generation
oversize is 413, unsupported content is 415). RegisterInput/LoginInput require
email/password. GenerateInput requires referenceFile. LutSettings requires
styleParams/adjustments. SaveLookInput requires name/thumbnail/styleParams/adjustments;
RenameLookInput requires a nonblank name. No-body operations have no requestBody,
including logout and favorite. Every path id is required, opaque, and not assumed
to be a UUID. No list query/pagination is defined. Empty lists return `[]`.
204 responses have no content; clients must not parse JSON from them.

User requires id/email. AuthResult requires user/access_token/token_type (`bearer`).
StyleParams requires id/shadowTint/highlightTint/baseSaturation; RGB tints have
exactly three normalized numbers. Adjustments requires all four numbers, even
when using default values (80/0/0/0); missing values are not silently defaulted.
Intensity is 0..100, others -50..50. LutData requires size/data. Look requires
id/name/style_params/adjustments/thumbnail_url/is_favorite/created_at/updated_at.
Error requires code/message; codes are validation/auth/not_found/unknown.

## Wire and service boundaries

- Register/login retain the token centrally and return nested User. getMe maps
  only unauthenticated 401 to null; network/server errors remain errors.
- Logout requires bearer auth, revokes only the current token, returns empty 204,
  and returns 401 for missing/invalid/expired/revoked tokens. Client credentials
  and auth state clear even after 401 or failed revocation. The real adapter uses
  tab-scoped sessionStorage keyed by API base; the mock has in-memory auth only.
- Generation sends actual browser File bytes and filename as FormData field
  `referenceFile`, leaving multipart Content-Type/boundary to the browser. The
  inclusive limit is **15,728,640 bytes** (UI: 15 MB); the next byte fails. UI/mock
  check MIME/size; backend signature and decoding checks determine image validity.
- Look maps style_params→styleParams, thumbnail_url→thumbnail,
  is_favorite→favorite, created_at→createdAt. Required updated_at is validated as
  epoch milliseconds and deliberately omitted from the current UI model. Neither
  timestamp is converted from seconds or parsed as a date. Empty thumbnail and
  false favorite are valid. Save inputs and nested StyleParams keep camelCase.
- Names trim on save/rename; blank save becomes `Untitled look`, blank rename
  fails. Owners are private; foreign and missing ids share 404. Favorite is an
  atomic inversion and must not be automatically retried.
- LUT JSON data becomes Float32Array: exactly **107,811** samples at size **33**,
  interleaved RGB, red grid index fastest, then green, then blue:
  `data[3*((b*33+g)*33+r)+c]`. No reordering or browser adjustment formulas.
  Cube export uses the same settings/builder and 35,937 RGB rows; nine significant
  decimal digits round-trip float32 samples. Parsed cube data must exactly equal
  renderLut after float32 conversion. PNG/JPEG export applies that same LUT.
- Input/output are encoded SDR sRGB/Rec.709, normalized 0..1; no HDR/log transform.
  Generation is guest-accessible and persists no originals. Only explicit
  authenticated saves store numeric settings and an optional 256 px JPEG thumbnail.

## Verification

From `backend/` after `uv sync --locked`:

```sh
uv run python ../_docs/check-contract.py
uv run pytest tests/test_api.py tests/test_download.py tests/test_render.py
```

The audit check verifies interface/table/operation agreement, explicit security,
request and response shapes/statuses, local reference resolution and JSON Schema
2020-12 validity. Backend tests verify live API behavior and float32 parity;
frontend adapter suites verify conversions. This is a focused structural/semantic
audit, not certification by a full OpenAPI conformance validator.

Mock limitations remain intentional: generation is a file-size-varied synthetic
look, auth/Library are memory-only, and its six-decimal cube writer is not the
real backend's exact float32 export. Do not use mock results as photographic
quality, persistence, or real cube-parity evidence.
