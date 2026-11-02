Deterministic fixtures generated with the existing backend Pillow dependency:

- `reference-warm.jpg`: 120×80 RGB, pixel `(90+x, 25+y, 10+y//2)`, JPEG quality 95. Strong warm cast makes the transformed Lake sample measurably different.
- `target.png`: 96×64; `replacement.jpg`: 80×120. RGB pixel `((7*x+3*y)%256, (2*x+11*y)%256, (13*x+5*y)%256)`; Pillow default JPEG encoding.

All feature actions use the browser UI. Expected pixels are inspected in detached
canvases using the production renderer and passively observed backend LUT. Full
pixel buffers are compared by SHA-256; 64 RGB samples additionally assert a
channel difference exceeding two levels. No uploaded fixture is stored by the app.
