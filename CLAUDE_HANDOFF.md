# What to tell Claude — the automation is already fixed (2026-10-25)

Paste this block to Claude once. It ends the cookie loop forever and hands Claude
the correct mental model of how your image pipeline now works.

---

## Paste to Claude:

> Updates to the image pipeline — this changes how you help me:
>
> 1. **The cookie problem is permanently fixed — stop giving me cookie instructions.**
>    The bridge (server.py on the autopilot branch) now has three layers and never stalls:
>    Layer 1: official Gemini API with my free API key (GEMINI_API_KEY in cookies.env) —
>    best quality, no cookies, never expires. Its free image quota resets every morning.
>    Layer 2: my old web-session cookies — now just a fallback if the API quota runs out
>    during the day. Layer 3: pollinations.ai — zero-auth emergency fallback.
>    The UNAUTHENTICATED errors you saw were layer 2 dying; layer 1 now goes first, so
>    that error should mostly disappear. If a request fails with 429 (quota) or 402,
>    it means every free lane is momentarily exhausted — just tell me "image quota
>    spent, it auto-recovers after the daily reset" and queue the request again later.
>    Never ask me to re-paste __Secure-1PSID cookies again.
>
> 2. **The autopilot is a local agent already** — it polls the opswired-media repo every
>    45 seconds for new request files, generates the images on MY PC with my Gemini, and
>    pushes them back. You don't need to make images yourself or wait on me: write a
>    request JSON to the `requests/` folder of the repo, and the finished PNGs arrive on
>    the branch for you to reference. That's the zero-manual-steps loop.
>
> 3. **My standing design directives (apply to every new image automatically):**
>    OpsWired brand: violet as the core color, logo in the colored version with white
>    or navy text on dark backgrounds. No category labels like "14 - real estate" on
>    the images. Premium, elite look (01-03 quality), never generic stock feel.
>
> 4. **Scheduling:** once images for a post are ready, draft the post text and add it
>    to the schedule queue (posts since 04 and up, elite quality). I approve from Telegram.
>
> If a batch fails, check `D:\bots\autopilot\autopilot_restart.log` (my local copy) or
> the `status/` folder on the autopilot branch before asking me anything.

---

## Your side (one-time, already done for you):

- `GEMINI_API_KEY` is injected into `D:\bots\autopilot\cookies.env` (your engine's key).
- `AUTOPILOT_BACKGROUND.vbs` now starts the autopilot silently — double-click it, or
  put a shortcut in `shell:startup` so it boots with Windows.
- Bridge v2 is committed and pushed to the autopilot branch (3ca2b91).
