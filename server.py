#!/usr/bin/env python3
"""
OpsWired x Gemini bridge  (runs on YOUR PC, uses your logged-in Gemini web session - no API billing)

THREE WAYS TO USE THIS ONE FILE
  1. python server.py --test                   -> makes ONE image to prove cookies + library work
  2. python server.py --batch                  -> reads prompts.json (same folder), makes every asset, writes opswired_assets.zip
     python server.py --batch --only team_laptop obj_funnel
  3. (no flag)                                 -> MCP server for Claude Desktop (see claude_desktop_config.json)

COOKIES  (never paste them in a chat, never put this folder in Drive/GitHub)
  Set two environment variables, or put them in the Claude Desktop config "env" block:
     GEMINI_PSID    = value of cookie  __Secure-1PSID   (gemini.google.com -> F12 -> Application -> Cookies)
     GEMINI_PSIDTS  = value of cookie  __Secure-1PSIDTS
  They are the keys to your Google session; they expire every few weeks - just copy fresh ones then.

SETUP
  pip install gemini-webapi pillow "mcp<2"        (the quotes matter: mcp 2.x breaks the old import)
"""
import asyncio, json, os, pathlib, sys, time, zipfile

HERE = pathlib.Path(__file__).parent
OUT = pathlib.Path(os.environ.get("OPSWIRED_OUT") or HERE / "assets")
PSID = os.environ.get("GEMINI_PSID", "").strip()
PSIDTS = os.environ.get("GEMINI_PSIDTS", "").strip()
GAP_SECONDS = float(os.environ.get("OPSWIRED_GAP", "6"))   # pause between images, avoids rate limits

_client = None
_jobs = {}  # background batch state


# ----------------------------------------------------------------- core
async def client():
    global _client
    if _client is None:
        if not PSID:
            raise RuntimeError("GEMINI_PSID is not set (see the top of server.py).")
        from gemini_webapi import GeminiClient
        c = GeminiClient(PSID, PSIDTS or None)
        await c.init(timeout=120, auto_close=False, auto_refresh=True)
        _client = c
    return _client


def build_prompt(item, styles):
    ratio = item.get("ratio", "1:1")
    orient = {"4:5": "portrait 4:5", "3:2": "landscape 3:2", "1:1": "square 1:1", "16:9": "wide 16:9", "9:16": "tall 9:16"}.get(ratio, ratio)
    return f"Generate an image ({orient} aspect ratio). {item['prompt'].strip()} {styles[item['style']].strip()}"


async def make_image(prompt, dest: pathlib.Path):
    """One image -> dest (PNG). Returns a status string. Never retries silently."""
    if dest.exists():
        return f"skip (exists): {dest.name}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        c = await client()
        resp = await c.generate_content(prompt)
        imgs = list(resp.images or [])
        if not imgs:
            return f"NO IMAGE for {dest.name}: Gemini answered with text only -> " + (resp.text or "")[:160].replace("\n", " ")
        saved = await imgs[0].save(path=str(dest.parent), filename=dest.name)
        saved = pathlib.Path(saved)
        if saved != dest:
            saved.replace(dest)
        try:  # make sure it is a real PNG whatever Google sent
            from PIL import Image
            im = Image.open(dest)
            if im.format != "PNG":
                im.convert("RGBA").save(dest, "PNG")
        except Exception:
            pass
        return f"saved: {dest.name}"
    except Exception as e:
        return f"FAILED {dest.name}: {str(e)[:220]}"


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
        """Check the Gemini image bridge: shows output folder and whether the Gemini session works."""
        try:
            await client()
            return f"OK. Gemini session is live. Output folder: {OUT}"
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
