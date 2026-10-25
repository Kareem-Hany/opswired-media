#!/usr/bin/env python3
"""
OpsWired x Gemini bridge  (runs on YOUR PC)

AUTH - TWO MODES, PICK BY WHAT IS SET (API key wins; it never expires like cookies):
  A) GEMINI_API_KEY = a free Google AI Studio API key (RECOMMENDED - official endpoint,
     no cookies, no expiry, same key style the JOB BRO engine already uses).
     Get one: aistudio.google.com -> Get API key. Put it in cookies.env:
         GEMINI_API_KEY=AIza...
  B) GEMINI_PSID / GEMINI_PSIDTS  (legacy web-session cookies - expire every few weeks)

THREE WAYS TO USE THIS ONE FILE
  1. python server.py --test                   -> makes ONE image to prove the bridge works
  2. python server.py --batch                  -> reads prompts.json (same folder), makes every asset, writes opswired_assets.zip
     python server.py --batch --only team_laptop obj_funnel
  3. (no flag)                                 -> MCP server for Claude Desktop (see claude_desktop_config.json)

SETUP
  pip install httpx pillow "mcp<2"        (the quotes matter: mcp 2.x breaks the old import)
  pip install gemini-webapi                (only needed if you use legacy cookie mode B)
"""
import asyncio, base64, json, os, pathlib, sys, time, zipfile

HERE = pathlib.Path(__file__).parent

# Self-load cookies.env (works standalone: --test, --batch, MCP; autopilot.py also loads it)
_env_file = HERE / "cookies.env"
if _env_file.exists():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        if "=" in _line and not _line.strip().startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

OUT = pathlib.Path(os.environ.get("OPSWIRED_OUT") or HERE / "assets")
API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
PSID = os.environ.get("GEMINI_PSID", "").strip()
PSIDTS = os.environ.get("GEMINI_PSIDTS", "").strip()
GAP_SECONDS = float(os.environ.get("OPSWIRED_GAP", "6"))   # pause between images, avoids rate limits

API_BASE = "https://generativelanguage.googleapis.com/v1beta"
# Ring verified live against a free AI Studio key (models list, 2026-10-25) — cheapest/limit-friendly first.
API_IMAGE_MODELS = ["gemini-3.1-flash-lite-image", "gemini-3.1-flash-image", "gemini-2.5-flash-image", "gemini-3.1-flash-image-preview", "gemini-nano-banana-2.1"]

_client = None
_jobs = {}  # background batch state


# ----------------------------------------------------------------- core
async def client():
    global _client
    if _client is None:
        if not PSID:
            raise RuntimeError("No GEMINI_API_KEY and no GEMINI_PSID set (see the top of server.py).")
        from gemini_webapi import GeminiClient
        c = GeminiClient(PSID, PSIDTS or None)
        await c.init(timeout=120, auto_close=False, auto_refresh=True)
        _client = c
    return _client


async def api_make_image(prompt: str, dest: pathlib.Path) -> str:
    """Official Gemini API image generation with an API key. Tries a small model ring
    so a retired/limited model falls through instead of breaking the batch."""
    import httpx

    body = {"contents": [{"parts": [{"text": prompt}]}]}
    last = "no model attempted"
    for model in API_IMAGE_MODELS:
        try:
            async with httpx.AsyncClient(timeout=120.0) as hc:
                resp = await hc.post(
                    f"{API_BASE}/models/{model}:generateContent",
                    headers={"x-goog-api-key": API_KEY, "Content-Type": "application/json"},
                    json=body,
                )
        except Exception as e:
            last = f"{model}: network {type(e).__name__}"
            continue
        if resp.status_code != 200:
            last = f"{model}: HTTP {resp.status_code}"
            if resp.status_code == 400 and "API_KEY" in resp.text[:400]:
                return f"FAILED {dest.name}: API key rejected - check GEMINI_API_KEY"
            continue  # 404 retired / 429 quota / 5xx -> next model
        parts = resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])
        img = next((p.get("inlineData") or p.get("inline_data") for p in parts if (p.get("inlineData") or p.get("inline_data"))), None)
        if not img:
            txt = " ".join(p.get("text", "") for p in parts if p.get("text"))[:140]
            last = f"{model}: text-only answer -> {txt}"
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(base64.b64decode(img["data"]))
        try:  # normalize whatever Google sent into a real PNG
            from PIL import Image
            im = Image.open(dest)
            if im.format != "PNG":
                im.convert("RGBA").save(dest, "PNG")
        except Exception:
            pass
        return f"saved: {dest.name} (API, {model})"
    return f"FAILED {dest.name}: {last}"


async def pollinations_image(prompt: str, dest: pathlib.Path) -> str:
    """Zero-auth fallback: pollinations.ai (free, no key, no cookies, unlimited).
    Used only when both the Gemini API quota and the web cookies are unavailable,
    so image-making never stalls while you sleep."""
    import urllib.parse

    import httpx

    dims = (1024, 1024)
    p = prompt.lower()
    if "4:5" in p:
        dims = (896, 1120)
    elif "3:2" in p:
        dims = (1216, 832)
    elif "16:9" in p:
        dims = (1344, 768)
    elif "9:16" in p:
        dims = (768, 1344)
    url = "https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt[:1500]) + f"?width={dims[0]}&height={dims[1]}&nologo=true"
    async with httpx.AsyncClient(timeout=180.0, follow_redirects=True) as hc:
        r = await hc.get(url)
    if r.status_code == 200 and r.content[:2] in (b"\xff\xd8", b"\x89P"):
        # QUARANTINE: fallback images must never mix with brand assets. Save under
        # _fallback/ so design pipelines can exclude them by path.
        dest = dest.parent / "_fallback" / dest.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(r.content)
        try:
            from PIL import Image
            im = Image.open(dest)
            if im.format != "PNG":
                im.convert("RGBA").save(dest, "PNG")
        except Exception:
            pass
        return f"saved (FALLBACK, quarantined): _fallback/{dest.name}"
    return f"FAILED {dest.name}: pollinations HTTP {r.status_code}"


def build_prompt(item, styles):
    ratio = item.get("ratio", "1:1")
    orient = {"4:5": "portrait 4:5", "3:2": "landscape 3:2", "1:1": "square 1:1", "16:9": "wide 16:9", "9:16": "tall 9:16"}.get(ratio, ratio)
    return f"Generate an image ({orient} aspect ratio). {item['prompt'].strip()} {styles[item['style']].strip()}"


async def make_image(prompt, dest: pathlib.Path):
    """One image -> dest (PNG). Three layers so it NEVER stalls:
    1) official Gemini API (best; quota resets daily)
    2) legacy web cookies (if still fresh)
    3) pollinations.ai (free, no auth, unlimited)"""
    if dest.exists():
        return f"skip (exists): {dest.name}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if API_KEY:
        r = await api_make_image(prompt, dest)
        if r.startswith("saved"):
            return r
        print(f"[bridge] API layer unavailable ({r.split(':', 1)[-1].strip()[:90]}) -> next layer", flush=True)
    if PSID:
        try:
            c = await client()
            resp = await c.generate_content(prompt)
            imgs = list(resp.images or [])
            if imgs:
                saved = await imgs[0].save(path=str(dest.parent), filename=dest.name)
                saved = pathlib.Path(saved)
                if saved != dest:
                    saved.replace(dest)
                try:
                    from PIL import Image
                    im = Image.open(dest)
                    if im.format != "PNG":
                        im.convert("RGBA").save(dest, "PNG")
                except Exception:
                    pass
                return f"saved: {dest.name} (web cookies)"
        except Exception as e:
            print(f"[bridge] cookie layer unavailable ({str(e)[:90]}) -> final layer", flush=True)
    return await pollinations_image(prompt, dest)


def load_spec(path=None):
    p = pathlib.Path(path) if path else HERE / "prompts.json"
    return json.loads(p.read_text(encoding="utf-8"))


def pack_zip(folder: pathlib.Path, zpath: pathlib.Path):
    pngs = sorted(folder.glob("*.png"))
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for p in pngs:
            z.write(p, p.name)
    return len(pngs)


async def run_batch(items, styles, folder, job=None):
    out = OUT / folder
    log = []
    for n, it in enumerate(items, 1):
        r = await make_image(build_prompt(it, styles), out / f"{it['name']}.png")
        log.append(r)
        print(f"[{n}/{len(items)}] {r}", flush=True)
        if job is not None:
            job["done"], job["log"] = n, log
        if not r.startswith("skip"):
            await asyncio.sleep(GAP_SECONDS)
    z = OUT / f"{folder}.zip"
    count = pack_zip(out, z)
    summary = f"{count} images in {z}"
    if job is not None:
        job["state"], job["summary"] = "finished", summary
    return summary, log


# ----------------------------------------------------------------- CLI modes
async def cli_test():
    print("Output folder:", OUT)
    r = await make_image("Generate an image (square 1:1 aspect ratio). A glossy 3D violet rocket on a plain white background, no text.", OUT / "_test" / "test_rocket.png")
    print(r)
    print("If it says 'saved', open that file: the bridge works." if r.startswith(("saved", "skip")) else "Not working yet: send the line above to Claude (never the cookies).")


async def cli_batch(only):
    spec = load_spec()
    items = [i for i in spec["assets"] if not only or i["name"] in only]
    print(f"{len(items)} assets, output {OUT / 'opswired'}")
    summary, log = await run_batch(items, spec["styles"], "opswired")
    bad = [l for l in log if l.startswith(("FAILED", "NO IMAGE"))]
    print("\nDONE:", summary, "|", len(bad), "problems")
    print("Attach this file to the Claude chat:", OUT / "opswired.zip")


# ----------------------------------------------------------------- MCP server (Claude Desktop)
def mcp_main():
    try:
        from mcp.server.fastmcp import FastMCP as Server       # mcp 1.x
    except ModuleNotFoundError:
        from mcp.server.mcpserver import MCPServer as Server   # mcp 2.x
    mcp = Server("opswired-gemini-images")

    @mcp.tool()
    async def bridge_status() -> str:
        """Check the Gemini image bridge: shows output folder and whether auth works."""
        if API_KEY:
            return f"OK. API-key mode (no cookies, never expires). Output folder: {OUT}"
        try:
            await client()
            return f"OK. Legacy web-session cookies live (consider adding GEMINI_API_KEY). Output folder: {OUT}"
        except Exception as e:
            return f"NOT READY: {e}"

    @mcp.tool()
    async def generate_image(prompt: str, filename: str, ratio: str = "1:1", folder: str = "opswired") -> str:
        """Generate ONE image (people, 3D object, background) with the user's Gemini and save it as a PNG on their PC.
        Put a plain white seamless background and 'no text, no logos' in the prompt when a cutout is wanted."""
        p = build_prompt({"prompt": prompt, "ratio": ratio, "style": "x"}, {"x": ""})
        return await make_image(p, OUT / folder / (filename if filename.endswith(".png") else filename + ".png"))

    @mcp.tool()
    async def start_batch_from_prompts_file(only: list[str] | None = None, folder: str = "opswired") -> str:
        """Start generating every asset in prompts.json (next to server.py) in the BACKGROUND. Returns at once; poll batch_status."""
        spec = load_spec()
        items = [i for i in spec["assets"] if not only or i["name"] in only]
        job = {"state": "running", "total": len(items), "done": 0, "log": [], "summary": ""}
        _jobs[folder] = job
        asyncio.get_running_loop().create_task(run_batch(items, spec["styles"], folder, job))
        return f"Started {len(items)} images. Poll batch_status(folder='{folder}') every minute or two."

    @mcp.tool()
    async def start_batch(assets: list[dict], folder: str = "opswired") -> str:
        """Start a custom batch in the BACKGROUND. assets = [{"name":"x","prompt":"...","ratio":"4:5"}]. Returns at once; poll batch_status."""
        items = [{"name": a["name"], "prompt": a["prompt"], "ratio": a.get("ratio", "1:1"), "style": "x"} for a in assets]
        job = {"state": "running", "total": len(items), "done": 0, "log": [], "summary": ""}
        _jobs[folder] = job
        asyncio.get_running_loop().create_task(run_batch(items, {"x": ""}, folder, job))
        return f"Started {len(items)} images."

    @mcp.tool()
    async def batch_status(folder: str = "opswired") -> str:
        """Progress of a background batch, with the last log lines and the zip path when finished."""
        j = _jobs.get(folder)
        if not j:
            return "No batch started in this session."
        return json.dumps({"state": j["state"], "done": j["done"], "total": j["total"], "summary": j["summary"], "last": j["log"][-4:]}, indent=1)

    mcp.run()


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--test" in a:
        asyncio.run(cli_test())
    elif "--batch" in a:
        only = a[a.index("--only") + 1:] if "--only" in a else None
        asyncio.run(cli_batch(only))
    else:
        mcp_main()
