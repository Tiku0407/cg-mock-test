# Leaderboard V2 — GitHub + Google Apps Script connection

This branch adds a standalone live leaderboard without changing the existing secure exam/grader flow.

## Files
- `leaderboard.html` — public Daily / Weekly / Monthly Top 10 page
- `apps-script/leaderboard.gs` — GET API that reads `सर्वर-परिणाम`
- Existing `grader.gs` remains unchanged.

## One-time Google Apps Script step
1. Open **CSPDCL मॉक टेस्ट स्कोर** Google Sheet.
2. Extensions → Apps Script.
3. Files + → Script → name it `leaderboard`.
4. Copy the complete contents of `apps-script/leaderboard.gs` into that file.
5. Save.
6. Deploy → **Manage deployments**.
7. Edit the CURRENT Web App deployment.
8. Version → **New version**.
9. Deploy. Do not create a new deployment; this keeps the same Web App URL.

## Test the API
Open:
`YOUR_WEB_APP_URL?action=leaderboard&type=daily`

You should receive JSON with:
- ok: true
- rows: [...]
- ranks 1–10

## GitHub Pages URL
After this branch is merged to main:
`https://tiku0407.github.io/cg-mock-test/leaderboard.html`

Daily, Weekly and Monthly buttons all use the same existing Web App URL.

## Ranking rule
- Source: `सर्वर-परिणाम`
- Only rows with स्थिति = जमा
- Best score per mobile in selected period
- Sort: highest score
- Tie 1: lower time
- Tie 2: more correct answers
- Top 10
