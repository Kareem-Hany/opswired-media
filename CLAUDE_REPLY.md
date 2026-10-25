# Reply to Claude — paste this whole block

Everything technical I raised is now fixed on my side. Here is the state and my answers:

## 1. Fallback images — segregated (your point accepted in full)
The bridge now saves fallback images ONLY to `assets/<batch>/_fallback/` and labels them
`saved (FALLBACK, quarantined)`. Rule for you: **anything under a `_fallback/` folder is
NEVER for posts.** Only PNGs directly inside `assets/<batch>/` are brand assets. The three
fallback images from batch3 are already quarantined there, and the repo is clean.

## 2. batch3 — the real numbers
3 of 12 saved (all fallbacks, now quarantined), 9 failed (the free image quota hit its
daily ceiling that evening, and the emergency lane was rate-limited too). The 9 missing
ones regenerate when the batch is re-requested after the daily reset (~10:00 Cairo).
I am re-running the missing 9 in the morning — you will see them arrive on the branch.

## 3. Push verification — built in
Every autopilot push now verifies with `git ls-remote` and writes `status/push.json`
(ok/fail + commit sha). The "12/12 locally but repo empty" case cannot silently recur.

## 4. The shared API key — clarification
Text models (what JOB BRO uses) and image models have **separate quota buckets**, so the
job engine does not drain the image quota — the 429s were the image batches hitting their
own free daily ceiling. Two options:
- (A, current) stay free: batches run within the daily image quota, resets ~10:00 Cairo.
- (B, optional) enable API billing on a separate Google project for a dedicated key —
  costs cents per image, removes the ceiling. That needs your card and your explicit go —
  I never touch billing myself. If you want it, create the key and put it in
  `D:\bots\autopilot\cookies.env` as `GEMINI_API_KEY=` on its own line; nothing else changes.

## 5. Autostart + watchdog — installed
Startup shortcuts exist for both the autopilot and a watchdog that restarts it if the
heartbeat goes stale. Cookies layer already uses auto_refresh; it is fallback-only now.

## 6. Design + WhatsApp
Go with your logo plan (colored logo on dark, white-on-violet, navy on light) and one
consistent footer position on every post. For WhatsApp: use **@opswired** as the visible
handle only if it is an actual registered WhatsApp username on my Business app — I will
confirm it; until I do, keep the number wa.me/201037604533 in captions and put "@opswired"
next to the other social icons. When I confirm the username, switch the footer to
@opswired everywhere.

## 7. Scheduling
You schedule directly (as agreed) — no Telegram sign-off for the 26–30 Oct plan.
Pinterest stays out until I give you the board name. If a post's image is missing or only
exists under `_fallback/`, hold that post and tell me — never substitute a fallback.
