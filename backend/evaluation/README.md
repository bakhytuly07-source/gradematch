# #18 color extraction experiment — NO-GO

Date: 2026-10-19. This is an engineering experiment, **not a passing extraction
implementation**. The production analyzer is unchanged. Do not wire this
experimental analyzer into generation or advance the remaining M3 issues on the
strength of this result.

## Decision and requirement

[Issue #18](https://github.com/bakhytuly07-source/gradematch/issues/18) requires:
“unresolved extraction failures block progression to the rest of the application
per plan section 15.” [Plan §15](../../_docs/plan.md#15-biggest-technical-risk-and-first-milestone)
says: “If the proof of concept cannot produce convincing results, improve the
algorithm before building the rest of the application.”

The calibrated revision still fails to preserve a neutral photographic reference
and substantially understates cool shadow colors. These are the core extraction
failures the gate was intended to expose. Neither valid finite LUTs nor passing
unit tests establish convincing transfer. Consequently #18 remains incomplete;
#19 and the later open M3 MVP issues have not been implemented in this batch.

## Reproduction and evidence

From `backend/`:

```sh
uv sync --locked
uv run pytest
uv run python evaluation/evaluate.py
node evaluation/browser-benchmark.cjs
```

The optional browser measurement uses Playwright provided by the execution
environment, the existing frontend TypeScript compiler, and `/usr/bin/chromium`.
It adds no project dependency. Run it **after** evaluate.py creates the ignored
browser-lut.json. browser-results.json records the exact LUT's SHA-256.

Sources are the repository's existing bundled sample-portrait.jpg,
sample-lake.jpg and sample-cafe.jpg. No new external photos were downloaded.
Generated images are explicit synthetic evaluation fixtures, never user uploads.
Reference styles are made by applying known transforms to these photos, which
provides a diagnostic expected result for every other target. This evaluates
transfer on photographic scenes, not recovery of an unknown real-world grade.
The experiment is not independent of the builder; a broader external-reference
set would still be needed after this basic controlled test passes.

Each board has columns: reference, target before, v1 tonal means, v2 neutral
anchors, v3 calibrated anchors, and the known grade applied to that target.
Rows are portrait, landscape, indoor. All three revisions are retained side by
side so the iteration can be reviewed rather than judged only from the latest
result.

- [Split shadows/highlights](comparison-split.jpg): cool shadows and warm highlights.
- [Muted warm look](comparison-muted.jpg): reduced saturation and warm balance.
- [Cool look](comparison-cool.jpg): cool shadows and highlights.
- [Neutral photographic control](comparison-neutral.jpg): identity grade on portrait.
- [All per-pair measurements and host information](results.json).
- [Chromium preview and full-resolution measurements](browser-results.json).

The achromatic ramp is an additional neutral control in test_extraction.py;
it passes without injecting tint or saturation. The photographic control is
harder because a neutral *grade* does not imply an achromatic *scene*.

## Iterations and observations

v1 uses tonal-band channel means with the same 0.25 tint attenuation as the
existing builder. It understates almost every reference, and its saturation
estimate stays near one even for the muted reference. v2 uses the least chromatic
20% of each tonal band to reduce subject-color contamination. That reduces some
false warm casts, but also removes valid highlight style information. v3 reverses
the builder's factor-of-four attenuation for tint and tries a wider chroma-based
saturation estimate. This increases visibility but confuses low scene chroma
with deliberate desaturation. No universal warm tint or contrast increase is
applied, but scene-content saturation bias remains.

For split references, v3 produces cooler shadows on all targets, but warm
highlights are substantially missing; saturation is too low. For muted references,
landscape desaturation moves in the intended direction, while skin and indoor
colors lose too much chroma and the warm highlight character is weak. Cool
references leave portrait shadows close to neutral and understate cool balance
on landscape and indoor targets. Contrast is largely inherited from the target,
not extracted: StyleParams exposes two tints and baseSaturation, with no base
contrast field. The experiment does not change that contract or claim contrast
recovery.

Most decisively, the neutral portrait reference causes v3 landscape chroma to
fall from 0.187 to 0.066 and indoor chroma from 0.129 to 0.045. This is unwanted
desaturation, not a reusable neutral style. v2 avoids the worst regression but
still fails the other references. Choosing it solely for neutrality would hide
the failed extraction rather than resolve it.

The following table records each pair's signed shadow/highlight color-balance
change, chroma change, and contrast change. Balance is mean channel minus mean
RGB, reported as RGB triples; contrast is luminance p90 minus p10. Values are v3
minus target-before in normalized encoded SDR RGB. These are descriptive
measurements, not perceptual pass scores. The JSON also includes v1/v2 and the
known-grade values for comparison.

| Reference → target | Shadow ΔRGB | Highlight ΔRGB | Chroma Δ | Contrast Δ | Diagnosis |
|---|---|---|---:|---:|---|
| split → portrait | -0.040, -0.009, +0.049 | -0.015, +0.001, +0.015 | +0.028 | +0.014 | Cool shadows visible; warm highlights weak, saturation too low. |
| split → landscape | -0.027, -0.012, +0.038 | +0.033, +0.004, -0.037 | -0.008 | +0.009 | Cool shadows visible; warm highlights weak, saturation too low. |
| split → indoor | -0.052, -0.009, +0.061 | -0.004, -0.003, +0.007 | -0.048 | +0.015 | Cool shadows visible; warm highlights weak, saturation too low. |
| muted → portrait | -0.003, +0.004, -0.001 | -0.011, +0.003, +0.008 | -0.017 | -0.002 | Muted direction visible; warm balance weak, skin/indoor transfer incomplete. |
| muted → landscape | +0.011, -0.005, -0.007 | +0.078, +0.011, -0.089 | -0.087 | -0.002 | Muted direction visible; warm balance weak, skin/indoor transfer incomplete. |
| muted → indoor | -0.034, +0.005, +0.029 | +0.003, -0.004, +0.001 | -0.065 | -0.003 | Muted direction visible; warm balance weak, skin/indoor transfer incomplete. |
| cool → portrait | -0.004, -0.002, +0.006 | -0.019, +0.006, +0.013 | -0.004 | +0.005 | Cool shadow transfer too weak; scene colors dominate. |
| cool → landscape | +0.000, -0.004, +0.004 | +0.022, +0.009, -0.031 | -0.026 | +0.002 | Cool shadow transfer too weak; scene colors dominate. |
| cool → indoor | -0.019, -0.001, +0.020 | -0.014, +0.004, +0.010 | -0.030 | +0.005 | Cool shadow transfer too weak; scene colors dominate. |
| neutral → portrait | -0.002, +0.002, +0.000 | -0.007, +0.003, +0.004 | -0.021 | +0.001 | FAIL: unwanted desaturation from neutral photographic reference. |
| neutral → landscape | +0.018, -0.010, -0.009 | +0.110, +0.011, -0.120 | -0.121 | +0.001 | FAIL: unwanted desaturation from neutral photographic reference. |
| neutral → indoor | -0.041, +0.002, +0.038 | +0.014, -0.008, -0.006 | -0.085 | -0.000 | FAIL: unwanted desaturation from neutral photographic reference. |

## Performance and limits

Measured on the managed **cloud host**, Intel Xeon Platinum 8573C, Linux x86_64,
Python 3.12.14; Chromium 154.0.8037.57 exposes three logical workers. This is **not
laptop qualification**. Timings use perf_counter in Python and performance.now
in Chromium.

The generation fixture is a 4000×3000 JPEG resized from the bundled landscape,
padded to exactly 15,728,640 bytes. Padding exercises the byte boundary but is
not a worst-case high-entropy 15 MB camera photo. Five decode + analysis + LUT
runs took 301, 298, 285, 264 and 311 ms (under the 5 s target locally). Analysis
is capped at 1024 px longest side. Pillow's 12 MP LUT application took 250 ms.
Only generated fixtures are saved as evidence.

Browser timing uses the existing applyLutToPixels function, getImageData,
putImageData and one requestAnimationFrame. No adjustment formula is recreated
in the browser. For 1024×768 pixels: cold 78 ms, five warm runs 39–41 ms. For
4000×3000 pixels: cold 617 ms, warm 571–972 ms. These renderer-only timings
exclude control events, network transfer and API JSON serialization. They do
not establish complete control-to-preview ≤300 ms. Exact samples, method,
browser identity and LUT digest are in browser-results.json.

## Remaining work before a go decision

Improve scene/grade separation without tuning to these three photos, then rerun
all references and controls. Investigate robust tonal regression and a principled
saturation estimate instead of scaling average scene chroma. Preserve the neutral
photographic control as a mandatory visual regression. Assess the contrast
requirement against the current StyleParams contract before promising contrast
extraction. Once controlled transfers pass, add independent references and repeat
complete generation/control-to-preview measurements on laptop hardware.

Unit tests protect determinism, bounds, analysis size and the achromatic control;
they do not label failed photographic transfers as passing quality tests.
