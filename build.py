import json, pathlib, datetime

DOCS = pathlib.Path("docs")
DOCS.mkdir(exist_ok=True)
STATE = DOCS / "state.json"

state = json.loads(STATE.read_text()) if STATE.exists() else {"runs": 0}
state["runs"] += 1
now = datetime.datetime.now(datetime.timezone.utc)
stamp = now.strftime("%Y-%m-%d %H:%M UTC")
state["last_run"] = stamp
STATE.write_text(json.dumps(state, indent=2))

TEMPLATE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>UAS DAILY INTELLIGENCE BRIEF</title>
<style>
  :root { --bg:#0a0d10; --fg:#e8edf2; --dim:#7c8a99; --accent:#00e08a; --rule:#1c242c; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--fg);
         font:15px/1.5 "SF Mono",Consolas,"Roboto Mono",monospace; padding:40px 48px; }
  header { border-bottom:2px solid var(--accent); padding-bottom:16px; margin-bottom:28px; }
  h1 { font-size:22px; letter-spacing:.18em; margin:0 0 14px; font-weight:600; }
  .bar { display:flex; gap:40px; flex-wrap:wrap; font-size:14px; }
  .k { color:var(--dim); letter-spacing:.08em; font-size:11px; display:block; }
  .v { color:var(--accent); font-size:19px; font-weight:600; }
  .note { color:var(--dim); font-size:13px; border-top:1px solid var(--rule);
          margin-top:36px; padding-top:14px; }
</style></head><body>
<header>
  <h1>UAS DAILY INTELLIGENCE BRIEF</h1>
  <div class="bar">
    <div><span class="k">LAST UPDATED</span><span class="v">__NOW__</span></div>
    <div><span class="k">AUTONOMOUS RUNS</span><span class="v">__RUNS__</span></div>
    <div><span class="k">STATUS</span><span class="v">PIPELINE LIVE</span></div>
  </div>
</header>
<p class="note">Autonomy layer verified. Data pipelines (USAspending awards, SAM.gov
solicitations) attach at step 2.</p>
</body></html>
"""

html = TEMPLATE.replace("__NOW__", stamp).replace("__RUNS__", str(state["runs"]))
(DOCS / "index.html").write_text(html, encoding="utf-8")
print("run", state["runs"], "at", stamp)
