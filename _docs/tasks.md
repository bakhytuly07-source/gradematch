## 1. Harden reference upload validation
Milestone: M1
Label: mvp
Goal: Reject invalid reference files before generation.
Description: Extend the existing upload and mockService validation for empty files, unsupported formats and the 15 MB boundary. Keep the existing layout and add focused validation regression tests.

## 2. Harden target photo loading
Milestone: M1
Label: mvp
Goal: Keep the current preview usable when target loading fails.
Description: Validate target JPEG, PNG and WebP files and handle decode failures in the existing upload flow. Release replaced object URLs and show an actionable retry message.

## 3. Add bundled sample target photos
Milestone: M1
Label: mvp
Goal: Let guests test a look without uploading a target.
Description: Add a small licensed set covering portraits, landscapes and mixed lighting to the existing sample picker. Record attribution and verify each sample loads without an external network request.

## 4. Handle generation failures and retries
Milestone: M1
Label: mvp
Goal: Recover cleanly from a failed Generate Color Style request.
Description: Use mockService failure injection to exercise pending, failure and retry states in the existing editor. Prevent duplicate submissions and preserve the chosen reference on failure.

## 5. Prevent stale preview updates
Milestone: M1
Label: mvp
Goal: Show only the LUT for the latest selected settings.
Description: Harden the existing four-control flow against overlapping renderLut promises and rejected renders. Add a regression test with deliberately reordered responses.

## 6. Harden comparison controls
Milestone: M1
Label: mvp
Goal: Make both existing comparison modes reliable and accessible.
Description: Verify the before/after divider and side-by-side view across target replacements and narrow screens. Add keyboard support and accessible names where missing without rebuilding the editor.

## 7. Harden mock LUT exports
Milestone: M1
Label: mvp
Goal: Download the current mock LUT with all four adjustments.
Description: Exercise downloadLutCube with changed intensity, contrast, saturation and warmth in the current export flow. Handle failures and verify the exported samples match renderLut output.

## 8. Harden edited image exports
Milestone: M1
Label: mvp
Goal: Download the current target preview as PNG or JPEG.
Description: Check the existing image export path uses the active LUT and requested encoding. Handle canvas failures and release temporary download URLs with focused tests.

## 9. Harden account forms
Milestone: M1
Label: mvp
Goal: Show useful validation and authentication feedback.
Description: Extend the current login and registration forms for invalid email, short passwords and mock authentication failures. Test pending controls and recovery while keeping guest generation available.

## 10. Harden Library loading states
Milestone: M1
Label: mvp
Goal: Make the existing Library resilient to empty and failed loads.
Description: Exercise mockService listLooks and getLook with empty, delayed, missing and failed responses. Keep retry and signed-out guidance visible and add focused UI tests.

## 11. Harden Library mutations
Milestone: M1
Label: mvp
Goal: Keep saved-look actions consistent after mock failures.
Description: Test save, rename, favorite and delete in the existing Library including blank names and rejected mutations. Prevent duplicate actions and reconcile displayed data after successful retries.

## 12. Expand mock service isolation tests
Milestone: M1
Label: mvp
Goal: Keep the mock service a dependable frontend test boundary.
Description: Extend frontend/src/services/services.test.ts with duplicate accounts, cross-user access and immutable returned-look checks. Use zero injected latency and verify logout removes access to private Library actions.

## 13. Establish the 13-operation OpenAPI contract
Milestone: M2
Label: mvp
Goal: Define the missing root openapi.yaml from the service interface.
Description: Inventory all 13 GradeMatchService methods and map each to an explicit operationId, HTTP method and route. Document any client-only logout behavior and choose its API operation deliberately so the contract covers all 13 operations.

## 14. Specify API schemas and field conventions
Milestone: M2
Label: mvp
Goal: Make wire payloads unambiguous for both implementations.
Description: Define snake_case user, style, adjustment, look and auth schemas including access_token and timestamp representations. Specify numeric ranges, defaults, favorite semantics and the exact red-fastest 33-cubed LUT array layout.

## 15. Specify uploads, downloads and API errors
Milestone: M2
Label: mvp
Goal: Describe binary transfers and failure behavior in the contract.
Description: Define multipart reference uploads, the 15 MB limit, JPEG/PNG/WebP signatures and text .cube download responses. Specify bearer security, owner-scoped 404s, validation errors and getMe 401 without restricting guest color operations.

## 16. Validate contract examples against services
Milestone: M2
Label: mvp
Goal: Catch gaps before backend implementation.
Description: Validate openapi.yaml syntax, references and examples using approved existing tooling. Record the mapping of all 13 service methods to operations and check examples for auth, look mutations and LUT download.

## 17. Bootstrap an empty FastAPI application
Milestone: M3
Label: mvp
Goal: Start backend work with a passing smoke test.
Description: Create the minimal Python 3.12 FastAPI project under backend using uv and the approved stack after confirming dependency approval. Add a single app-startup pytest that passes before implementing the color engine or product endpoints.

## 18. Prove reusable color extraction on varied images
Milestone: M3
Label: mvp
Goal: Resolve the color-engine risk from plan.md section 15.
Description: Build a small deterministic analyzer and 33-cubed LUT prototype, then apply it to several different target scenes. Record reference comparisons, check for generic tint or contrast bias, iterate until convincing and benchmark browser preview plus full-resolution processing before proceeding.

## 19. Write standard .cube files from LUT data
Milestone: M3
Label: mvp
Goal: Export the same numeric transformation used for preview.
Description: Implement a pure red-fastest .cube writer with title, size and domain headers for 33 x 33 x 33 data. Check 35937 rows, finite bounded channels and identity round-trip fixtures before adding endpoints.

## 20. Define validated backend request models
Milestone: M3
Label: mvp
Goal: Enforce the agreed wire schemas at the API boundary.
Description: Implement contract-aligned models for users, style parameters, look data and exactly four adjustments. Reject nonfinite values, malformed channel triples and out-of-range controls with the documented error format.

## 21. Validate and decode uploads in memory
Milestone: M3
Label: mvp
Goal: Accept safe reference images without retaining originals.
Description: Build a bounded in-memory decoder for JPEG, PNG and WebP using file signatures and the 15 MB limit. Reject corrupt or oversized decoded images and create an orientation-correct analysis copy at most 1024 px on its longest side.

## 22. Implement backend adjustment composition
Milestone: M3
Label: mvp
Goal: Apply all four controls to the generated transformation.
Description: Compose intensity, contrast, saturation and warmth into the shared 33-cubed LUT using explicit SDR color assumptions. Test neutral identity, control boundaries and deterministic finite output without browser-side adjustment formulas.

## 23. Implement generateLook operation
Milestone: M3
Label: mvp
Goal: Generate numeric style parameters for guests.
Description: Connect the contracted generateLook multipart endpoint to the in-memory decoder and proven analyzer. Return only the documented numeric style payload and discard reference bytes on success and failure.

## 24. Implement renderLut operation
Milestone: M3
Label: mvp
Goal: Return the authoritative adjusted LUT to guests.
Description: Implement the contracted renderLut endpoint using validated style parameters and adjustments. Verify red-fastest ordering, array length and predictable errors for invalid inputs.

## 25. Implement downloadLutCube operation
Milestone: M3
Label: mvp
Goal: Download the authoritative adjusted transformation.
Description: Connect downloadLutCube to the same LUT builder used by renderLut and the .cube writer. Return the contracted content type and download filename and compare parsed output against renderLut samples.

## 26. Implement in-memory account storage and password hashing
Milestone: M3
Label: mvp
Goal: Keep backend credentials separate from public user data.
Description: Add an injectable in-memory user repository with normalized unique emails and bcrypt password hashes. Test duplicate-email handling and ensure plaintext passwords and hashes never appear in public responses or logs.

## 27. Implement register operation
Milestone: M3
Label: mvp
Goal: Create an account and establish authenticated access.
Description: Implement register against the in-memory user repository with contract validation and token issuance. Test successful registration, duplicate email and invalid credentials while keeping guest processing unauthenticated.

## 28. Implement login operation
Milestone: M3
Label: mvp
Goal: Authenticate existing users with bearer tokens.
Description: Implement login with bcrypt verification and the contracted access_token response. Use generic invalid-credential errors and test normalized email plus incorrect-password cases.

## 29. Implement getMe and logout operations
Milestone: M3
Label: mvp
Goal: Resolve and end bearer sessions according to the contract.
Description: Add shared bearer validation and implement getMe plus the contracted logout behavior for in-memory sessions. Test absent, invalid, expired and logged-out tokens with the specified 401 responses.

## 30. Implement saveLook with thumbnail validation
Milestone: M3
Label: mvp
Goal: Save only explicitly requested Library data.
Description: Implement saveLook for authenticated users in an in-memory owner-scoped repository. Store numeric style parameters, adjustments and a validated 256 px JPEG thumbnail only, rejecting full-size or malformed thumbnail payloads.

## 31. Implement listLooks operation
Milestone: M3
Label: mvp
Goal: List only the authenticated user’s saved looks.
Description: Implement listLooks with the contracted ordering and response schema over the in-memory repository. Test empty results and isolation between two users without exposing internal owner fields.

## 32. Implement getLook operation
Milestone: M3
Label: mvp
Goal: Reopen an owned look with its saved settings.
Description: Implement getLook by identifier with the full contracted style, adjustments and thumbnail response. Return the same not-found behavior for missing and foreign-owned looks and verify saved settings reproduce the LUT.

## 33. Implement renameLook operation
Milestone: M3
Label: mvp
Goal: Rename owned looks without altering color data.
Description: Implement the contracted renameLook operation with trimmed nonempty names and updated timestamps. Test missing and foreign-owned IDs plus unchanged style parameters and adjustments.

## 34. Implement toggleFavorite operation
Milestone: M3
Label: mvp
Goal: Update an owned look’s favorite status.
Description: Implement toggleFavorite according to the contract’s toggle or explicit-state semantics. Test repeated requests and owner isolation while preserving all other saved fields.

## 35. Implement deleteLook operation
Milestone: M3
Label: mvp
Goal: Remove only the requested owned look.
Description: Implement deleteLook with the documented success status and missing-look behavior. Verify deletion removes the thumbnail and saved settings and cannot affect another account’s Library.

## 36. Verify in-memory API privacy and contract coverage
Milestone: M3
Label: mvp
Goal: Complete all 13 operations before adding persistence.
Description: Run a contract-driven API suite covering every operation, guest permissions and cross-user denial. Assert uploaded originals never reach disk or storage and record the in-memory backend run commands.

## 37. Configure SQLAlchemy sessions from DATABASE_URL
Milestone: M4
Label: mvp
Goal: Make persistence configurable without SQLite-specific behavior.
Description: Add SQLAlchemy 2 engine and request-scoped session configuration with SQLite as the default. Test session cleanup and a different configured URL without raw SQL.

## 38. Define the User ORM model
Milestone: M4
Label: mvp
Goal: Represent persisted accounts with portable fields.
Description: Model user id, unique normalized email, password_hash and created_at per plan.md section 17. Verify ORM round trips and ensure serialization excludes password_hash.

## 39. Define the Look ORM model
Milestone: M4
Label: mvp
Goal: Persist only approved Library data.
Description: Model look ownership, name, numeric style JSON, adjustments JSON, 256 px JPEG thumbnail, favorite and timestamps. Use portable ORM types and verify no field stores an uploaded original.

## 40. Create the initial Alembic migration
Milestone: M4
Label: mvp
Goal: Create the account and Library schema reproducibly.
Description: Configure Alembic against the ORM metadata and DATABASE_URL and generate the initial migration. Verify upgrade on an empty SQLite database and downgrade on a disposable database.

## 41. Implement the ORM user repository
Milestone: M4
Label: mvp
Goal: Replace account maps behind the existing repository boundary.
Description: Implement user lookup and creation through ORM sessions with unique-email conflict translation. Test normalized duplicate accounts and transaction rollback without changing API payloads.

## 42. Persist registration and login accounts
Milestone: M4
Label: mvp
Goal: Keep accounts usable across backend restarts.
Description: Wire the ORM user repository into register and login while preserving bcrypt and bearer behavior. Verify registration followed by a new application instance can authenticate the same account.

## 43. Implement ORM look creation and listing
Milestone: M4
Label: mvp
Goal: Persist saves and owner-filtered Library lists.
Description: Replace in-memory saveLook and listLooks repository paths with ORM operations. Verify saved numeric data, thumbnail bytes and deterministic ordering after reconnecting.

## 44. Implement ORM look retrieval
Milestone: M4
Label: mvp
Goal: Reload saved looks through owner-scoped ORM queries.
Description: Replace the getLook repository path with an owner-filtered ORM lookup. Test missing and foreign-owned identifiers and exact reconstruction of saved adjustments.

## 45. Implement ORM rename and favorite updates
Milestone: M4
Label: mvp
Goal: Persist Library metadata changes atomically.
Description: Replace renameLook and toggleFavorite repository paths using ORM updates and timestamps. Verify ownership filters, rollback on failure and unchanged color data.

## 46. Implement ORM look deletion
Milestone: M4
Label: mvp
Goal: Delete saved data without touching other accounts.
Description: Replace deleteLook with a transactional owner-scoped ORM deletion. Verify the row and thumbnail are gone after reconnecting and foreign-owned rows remain.

## 47. Verify repository parity with isolated databases
Milestone: M4
Label: mvp
Goal: Keep persistence behavior identical to the in-memory backend.
Description: Run the shared repository behavior cases against temporary SQLite databases and in-memory implementations. Check isolation, errors and transaction boundaries without making tests depend on shared local data.

## 48. Document persistent startup and migration workflow
Milestone: M4
Label: mvp
Goal: Make SQLite setup reproducible for a new contributor.
Description: Document DATABASE_URL, migration commands and local database placement using the ORM configuration. Verify restart persistence and explain that guests and uploaded original images are never persisted.

## 49. Add the real HTTP service adapter
Milestone: M5
Label: mvp
Goal: Switch implementations through the existing service boundary.
Description: Implement a GradeMatchService HTTP adapter for all contracted operations and select it using frontend API configuration. Keep UI network calls inside frontend/src/services and retain the mock implementation for isolated tests.

## 50. Map snake_case API payloads to camelCase models
Milestone: M5
Label: mvp
Goal: Preserve the existing frontend model interface.
Description: Add explicit request and response conversions for style_params, base_saturation, tint channels, is_favorite and timestamps as contracted. Test both directions and convert LUT arrays to Float32Array without altering sample ordering.

## 51. Use File instead of FileLike in generateLook
Milestone: M5
Label: mvp
Goal: Send actual reference bytes in multipart requests.
Description: Change generateLook to accept browser File across the shared interface, mock and call sites. Build FormData without manually setting its boundary and replace metadata-only generation fixtures with real File instances.

## 52. Store access_token and restore authenticated sessions
Milestone: M5
Label: mvp
Goal: Keep API authentication consistent across reloads.
Description: Consume register and login auth envelopes, store access_token using the documented browser storage strategy and attach Bearer headers centrally. Restore user state on reload and clear the stored token and auth notification state on logout.

## 53. Map getMe 401 to null
Milestone: M5
Label: mvp
Goal: Preserve the service’s signed-out return contract.
Description: Translate only getMe unauthorized responses into null and clear stale authentication state. Test that network failures and server errors remain visible errors instead of being treated as logout.

## 54. Configure frontend-to-backend CORS
Milestone: M5
Label: mvp
Goal: Allow the intended browser origin to call the API.
Description: Configure explicit development and deployment origin settings with required methods and Authorization headers. Verify upload and authenticated preflight requests and rejection of an unconfigured origin.

## 55. Connect the guest workflow to the real API
Milestone: M5
Label: mvp
Goal: Complete upload, generate, preview and LUT download without login.
Description: Exercise real generateLook, renderLut and downloadLutCube from the existing editor and map API errors to ServiceError feedback. Check real reference validation and verify the downloaded .cube uses the currently displayed settings.

## 56. Connect Library and accounts to the real API
Milestone: M5
Label: mvp
Goal: Make saved-look workflows survive browser reloads.
Description: Exercise registration, login, logout and all seven Library actions through the real adapter. Verify owner isolation, favorites, rename, deletion and reopening a look on a new target with saved adjustments.

## 57. Complete backend-LUT preview and image export rendering
Milestone: M5
Label: mvp
Goal: Apply the same returned LUT across browser rendering paths.
Description: Wire or finish WebGL LUT application with a CPU Web Worker fallback in the existing preview and PNG/JPEG export path. Compare output pixels within a documented tolerance and confirm neither path recreates the four adjustment formulas.

## 58. Measure and tune the 300 ms preview target
Milestone: M5
Label: mvp
Goal: Quantify control-to-preview latency on a laptop.
Description: Measure from control input through API LUT response to presented pixels for WebGL and worker fallback using a repeatable target fixture. Record hardware, image sizes and latency distribution against 300 ms and tune request scheduling or rendering if the target is missed.

## 59. Verify the complete guest journey
Milestone: M6
Label: mvp
Goal: Prove the MVP works without an account.
Description: Run an end-to-end flow with a reference, bundled sample and uploaded target through both comparison modes and all controls. Verify .cube, PNG and JPEG downloads reflect the same selected settings.

## 60. Verify persistent account and Library journeys
Milestone: M6
Label: mvp
Goal: Prove private saved looks remain usable after restart.
Description: Run end-to-end registration, logout, login, save, list, open, rename, favorite and delete against SQLite. Include a second user and reloads to check privacy and persistence.

## 61. Add upload and privacy regression coverage
Milestone: M6
Label: mvp
Goal: Protect the in-memory image-processing requirement.
Description: Exercise spoofed extensions, corrupt files, empty uploads and the exact size boundary through the API. Check failure cleanup and confirm only explicitly saved 256 px thumbnails and numeric data reach persistence.

## 62. Benchmark generation against the five-second target
Milestone: M6
Label: mvp
Goal: Measure real reference analysis time on a laptop.
Description: Benchmark valid images up to 15 MB through generateLook including decoding and 1024 px analysis downscaling. Record repeatable hardware and timings against five seconds and identify any remaining bottleneck.

## 63. Check cross-browser rendering and fallback behavior
Milestone: M6
Label: mvp
Goal: Keep previews and exports usable across supported browsers.
Description: Test WebGL rendering, forced worker fallback, comparison views and PNG/JPEG downloads in current major browsers. Record pixel tolerances and fix reproducible color or orientation discrepancies.

## 64. Polish accessibility and responsive error states
Milestone: M6
Label: mvp
Goal: Make the current interface usable with keyboard and small screens.
Description: Audit upload, comparison, adjustment, account and Library controls for focus, labels and readable failure messages. Fix bounded accessibility and responsive defects without redesigning the frontend.

## 65. Write user guidance and color limitations
Milestone: M6
Label: mvp
Goal: Explain the supported workflow and realistic matching expectations.
Description: Document guest use, Library accounts, four controls, exports and SDR sRGB/Rec.709 assumptions. Explain approximate reference-style recovery, supported files and limits, and exactly what is stored.

## 66. Document local setup and MVP release checks
Milestone: M6
Label: mvp
Goal: Make the completed project reproducible and reviewable.
Description: Document frontend/backend commands, DATABASE_URL, migrations, CORS, API configuration and focused test commands. Record a release checklist linking contract coverage, color proof-of-concept evidence and the five-second and 300 ms measurements.

## 67. Extract a reference frame from a short video
Milestone: M6
Label: post-mvp
Goal: Use one chosen video frame as a reference image.
Description: Design a bounded video upload and frame-picker flow with a single supported codec path. Feed only the selected decoded frame into generation and document limits and cleanup.

## 68. Add a Postgres deployment profile
Milestone: M6
Label: post-mvp
Goal: Run the ORM-backed service against Postgres.
Description: Add documented DATABASE_URL configuration and approved driver setup for a disposable Postgres instance. Run migrations and repository parity checks without adding database-specific application queries.

## 69. Package the backend in Docker
Milestone: M6
Label: post-mvp
Goal: Provide a reproducible backend container.
Description: Add a minimal production Docker build with approved dependency installation and runtime configuration. Verify startup and a smoke request without baking secrets or uploaded image storage into the image.

## 70. Add a CI validation workflow
Milestone: M6
Label: post-mvp
Goal: Run project checks on pull requests.
Description: Configure CI for frontend tests, backend tests and OpenAPI validation with isolated SQLite data. Pin supported runtimes and expose failures without including credentials in logs.

## 71. Add revocable public share links
Milestone: M6
Label: post-mvp
Goal: Let an owner share one saved look intentionally.
Description: Define contract changes first for creating and revoking opaque read-only look links. Add scoped access tests and a viewer that reveals no owner credentials or original image.

## 72. Add private look tags
Milestone: M6
Label: post-mvp
Goal: Organize a user’s Library with tags.
Description: Define a portable tag model and contract updates for assigning tags to owned looks. Add a small Library filter and verify tags remain private per account.

## 73. Add opt-in generation history
Milestone: M6
Label: post-mvp
Goal: Let users revisit recent generated styles.
Description: Define an explicit opt-in retention policy and contract for numeric generation history without original images. Add a bounded history view and deletion behavior with owner isolation.

## 74. Add a binary LUT response format
Milestone: M6
Label: post-mvp
Goal: Reduce LUT transfer size for live preview.
Description: Define a versioned binary encoding with explicit float endianness, dimensions and channel order. Add negotiated API and adapter support and compare payload size and decoded samples with JSON.

## 75. Add HEIC reference image support
Milestone: M6
Label: post-mvp
Goal: Accept a common phone-photo format.
Description: Evaluate and obtain approval for a HEIC decoder before changing the upload contract and validation. Add orientation and color-profile fixtures and preserve in-memory processing.

## 76. Add password reset by email
Milestone: M6
Label: post-mvp
Goal: Let account owners recover access securely.
Description: Define expiring single-use reset tokens and the request/reset contract before implementing a configured email provider. Test token reuse, expiry and generic account-discovery-safe responses.

## 77. Add email verification
Milestone: M6
Label: post-mvp
Goal: Confirm ownership of registered email addresses.
Description: Define verification token expiry and account states without blocking guest processing. Add the verification flow and tests for expired and reused links.

## 78. Add one social login provider
Milestone: M6
Label: post-mvp
Goal: Offer an alternative Library sign-in method.
Description: Design the OAuth callback contract and secure account-linking rules for one approved provider. Implement state validation and tests for existing email collisions.

## 79. Add an optional tint control
Milestone: M6
Label: post-mvp
Goal: Offer green-magenta correction in advanced mode.
Description: Extend the contract and saved adjustment schema with a backward-compatible neutral tint default. Implement tint in the backend LUT engine and verify preview/export equivalence.

## 80. Add a 65-point LUT export option
Milestone: M6
Label: post-mvp
Goal: Offer denser LUT sampling for demanding workflows.
Description: Extend the export contract with a validated 33 or 65 size choice while retaining the default. Measure memory and export size and verify identity ordering at both resolutions.

## 81. Add a bounded RAW decoding pilot
Milestone: M6
Label: post-mvp
Goal: Evaluate one camera RAW format as reference input.
Description: Select an approved decoder and one documented camera fixture before expanding accepted formats. Measure in-memory decoding, color conversion and resource limits for the pilot.

## 82. Add Library search and pagination
Milestone: M6
Label: post-mvp
Goal: Keep large personal Libraries usable.
Description: Define paginated owner-scoped list and name-search parameters in the contract. Update the Library to load pages with stable ordering and test empty searches.

## 83. Add look duplication
Milestone: M6
Label: post-mvp
Goal: Create a separately editable copy of a saved look.
Description: Define a duplicate operation that copies numeric settings and the existing thumbnail for the current owner. Expose a Library action and verify later renames or deletes do not alter the original.

## 84. Add account data export
Milestone: M6
Label: post-mvp
Goal: Let users retrieve their saved account data.
Description: Define an authenticated export of profile metadata, saved numeric looks and permitted thumbnails. Test ownership and document that original uploads are unavailable because they are never stored.

## 85. Add account deletion
Milestone: M6
Label: post-mvp
Goal: Let users remove their account and saved data.
Description: Define a confirmed authenticated deletion operation with token invalidation and ORM-managed removal of owned looks. Test complete deletion and continued isolation of other users.

## 86. Define a formal color-quality evaluation rubric
Milestone: M6
Label: post-mvp
Goal: Make future extraction improvements comparable.
Description: Build on the plan.md section 15 proof of concept with a licensed reference/target set and a repeatable human scoring rubric. Record baseline results for reusable style, scene-color bias and artifacts before evaluating algorithm changes.
