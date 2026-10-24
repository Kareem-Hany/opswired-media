# OpsWired studio inbox
Kareem's PC generates image assets (Gemini bridge). `push_assets.bat` copies them to `studio/inbox/` and pushes.
Claude (cloud) pulls `studio/inbox/*`, cuts them out, and builds the posts on the Design canvas.
Rules for assets: one subject, plain flat grey background, no text/logos. No secrets in this repo (never commit cookies/API keys).
