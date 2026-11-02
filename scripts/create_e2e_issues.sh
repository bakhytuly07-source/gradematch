#!/usr/bin/env bash
set -euo pipefail
gh label create e2e-test --color 0E8A16 2>/dev/null || true
gh api repos/:owner/:repo/milestones -f title="M8 E2E per feature" >/dev/null 2>&1 || true

mk() {
  gh issue create --label e2e-test --milestone "M8 E2E per feature" --title "E2E: $1" --body "Goal: $2

Description: $3 One Playwright spec file for this feature, run against the Docker Compose stack with make e2e."
}

mk "Reference upload validation" "A user who picks a bad reference file sees a clear message and can recover with a valid photo." "An empty file, an unsupported type such as GIF, a file over 15 MB and a corrupt JPEG are rejected with a visible message, and a valid photo is accepted afterwards."
mk "Generate Color Style" "A valid reference photo produces a color style." "Upload a valid JPG, click Generate Color Style, see progress and then the finished state; the generate request returns 200."
mk "Upload a target photo" "A user can test the style on their own photo." "After generating, upload a PNG or JPG as the target; the preview shows the target with the style applied."
mk "Use a sample photo" "A user without a photo of their own can try the look on a bundled sample." "Choose a sample photo; the preview updates and the comparison controls become available."
mk "Before and after slider" "A user can compare original and result by dragging a divider." "In Before / after mode the divider follows the pointer and the visible split changes."
mk "Side by side mode" "A user can see original and result next to each other." "Switch to Side by side and both images are visible; switching back to Before / after works."
mk "Look intensity control" "Changing Look intensity changes the preview and the exported LUT." "Move the slider; a new render-lut request is sent with the new value and the exported .cube differs from the default."
mk "Contrast control" "Changing Contrast changes the preview and the exported LUT." "Move the slider; a new render-lut request is sent with the new value and the exported .cube differs from the default."
mk "Saturation control" "Changing Saturation changes the preview and the exported LUT." "Move the slider; a new render-lut request is sent with the new value and the exported .cube differs from the default."
mk "Warmth control" "Changing Warmth changes the preview and the exported LUT." "Move the slider; a new render-lut request is sent with the new value and the exported .cube differs from the default."
mk "Download LUT (.cube)" "A user can download a valid .cube file that matches the current settings." "Click Download LUT (.cube); the file name ends with .cube, the header says LUT_3D_SIZE 33 and there are 35937 data rows."
mk "Download image as PNG" "A user can download the edited image as PNG." "Click the PNG download; a valid PNG file is saved."
mk "Download image as JPEG" "A user can download the edited image as JPEG." "Click the JPEG download; a valid JPEG file is saved."
mk "Register" "A new user can create an account." "Register with a unique email and a valid password and see the logged-in state; an invalid email, a short password and an existing email each show an error."
mk "Log in" "A registered user can log in." "Log in with correct credentials and see the logged-in state; a wrong password shows an error."
mk "Log out" "A logged-in user can log out." "After logout the header shows Log in again and the Library asks for login."
mk "Session survives reload" "A logged-in user stays logged in after a reload." "Reload the page and open a new tab; the user is still logged in."
mk "Save a look to the Library" "A logged-in user can save the current look." "Click Save to Library; a confirmation appears and the look is in the Library with a thumbnail; a guest is asked to log in instead."
mk "Library list and open a look" "A user can see saved looks and reopen one." "Open the Library, see the saved looks newest first, open one, and the four control values are restored."
mk "Rename a look" "A user can rename a saved look." "Rename a look and see the new name after a reload; a blank name is rejected with a message."
mk "Favorite a look" "A user can mark a saved look as favorite and unmark it." "Toggle the star; the state persists after a reload."
mk "Delete a look" "A user can delete a saved look." "Delete a look and it disappears from the Library and stays gone after a reload."
mk "Library requires login" "A guest cannot see the Library." "Open /library as a guest and the app asks to log in; after logging in the Library opens."
