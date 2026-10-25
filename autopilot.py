#!/usr/bin/env python3
"""
OpsWired AUTOPILOT  -  leave this window open and forget it.
It watches the 'autopilot' branch of your opswired-media GitHub repo for new request files, makes the
images with YOUR Gemini (same code as server.py that already worked), and pushes them back,
so Claude gets them with zero manual steps.

  Needs once:  pip install gemini-webapi pillow      and cookies.env next to this file (see README.txt)
  Start:       double-click start.bat   (or: python autopilot.py)
It only ever reads request files from your own repo, only calls Gemini, and only writes inside this folder.
"""
import asyncio, json, os, pathlib, subprocess, sys, time, datetime

HERE = pathlib.Path(__file__).resolve().parent
os.chdir(HERE)
env = HERE / "cookies.env"          # never committed (see .gitignore)
if env.exists():
    for line in env.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip().strip('"').strip("'")
os.environ["OPSWIRED_OUT"] = str(HERE / "assets")
sys.path.insert(0, str(HERE))
import server  # noqa: E402

GIT = ["git", "-c", "user.name=OpsWired Autopilot", "-c", "user.email=autopilot@opswired.local"]
POLL = 45


def git(*a):
    return subprocess.run(GIT + list(a), capture_output=True, text=True, cwd=HERE)


def push(msg):
    git("add", "-A")
    if not git("status", "--porcelain").stdout.strip():
        return True
    git("commit", "-m", msg)
    r = None
    for _ in range(3):
        git("pull", "--rebase", "--autostash", "-q")
        r = git("push", "-q", "origin", "HEAD")
        if r.returncode == 0:
            return True
        time.sleep(3)
    print("!! git push failed:", (r.stderr if r else "")[:300], flush=True)
    return False


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


def write_status(name, **kw):
    p = HERE / "status" / f"{name}.json"
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps({"time": now(), **kw}, indent=1), encoding="utf-8")


async def process(req_path):
    name = req_path.stem
    spec = json.loads(req_path.read_text(encoding="utf-8"))
    styles = json.loads((HERE / "styles.json").read_text(encoding="utf-8"))["styles"]
    styles.update(spec.get("styles", {}))
    items = spec["assets"]
    log, bad = [], 0
    write_status(name, state="running", done=0, total=len(items), log=log)
    push(f"autopilot: start {name}")
    for n, it in enumerate(items, 1):
        it.setdefault("style", "x")
        st = styles if it["style"] in styles else {**styles, it["style"]: ""}
        r = await server.make_image(server.build_prompt(it, st), HERE / "assets" / name / f"{it['name']}.png")
        print(f"[{name} {n}/{len(items)}] {r}", flush=True)
        log.append(r)
        if r.startswith(("FAILED", "NO IMAGE")):
            bad += 1
            if "UNAUTH" in r.upper() or "COOKIE" in r.upper():
                write_status(name, state="error", done=n, total=len(items), log=log,
                             hint="Gemini cookies expired: paste fresh ones into cookies.env and restart start.bat")
                push(f"autopilot: {name} cookie error")
                return False
        write_status(name, state="running", done=n, total=len(items), log=log)
        push(f"autopilot: {name} {n}/{len(items)} {it['name']}")
        if not r.startswith("skip"):
            await asyncio.sleep(server.GAP_SECONDS)
    write_status(name, state="finished", done=len(items), total=len(items), problems=bad, log=log)
    push(f"autopilot: finished {name}")
    return True


async def main():
    print("OpsWired autopilot running. Leave this window open. Ctrl+C to stop.", flush=True)
    last_beat = 0
    while True:
        git("pull", "--rebase", "--autostash", "-q")
        for rp in sorted((HERE / "requests").glob("*.json")):
            st = HERE / "status" / f"{rp.stem}.json"
            state = json.loads(st.read_text(encoding="utf-8")).get("state") if st.exists() else None
            if state in (None, "running", "error"):
                await process(rp)
        if time.time() - last_beat > 900:
            write_status("heartbeat", state="alive")
            push("autopilot: heartbeat")
            last_beat = time.time()
        await asyncio.sleep(POLL)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("stopped")
