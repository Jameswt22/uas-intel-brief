import json, pathlib, datetime, re, html, urllib.request, urllib.error

API = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
DOCS = pathlib.Path("docs"); DOCS.mkdir(exist_ok=True)
STATE = DOCS / "state.json"

QUERIES = [
    "unmanned aircraft system", "unmanned aerial vehicle", "unmanned aircraft",
    "MQ-9", "RQ-4", "ISR aircraft", "remotely piloted aircraft",
    "medium altitude long endurance", "tactical unmanned",
]

RELEVANT = re.compile(
    r"unmanned|drone|\bUAS\b|\bUAV\b|\bRPA\b|MQ-|RQ-|ISR|surveillance|reconnaissance|"
    r"loitering|fixed[- ]wing|airframe|ground control station|payload|electro-optical|"
    r"synthetic aperture|SIGINT|autonom", re.I)

COMPETITORS = {
    "SHIELD AI": "Shield AI", "ANDURIL": "Anduril", "GENERAL ATOMICS": "General Atomics",
    "KRATOS": "Kratos", "AEROVIRONMENT": "AeroVironment", "INSITU": "Insitu",
    "TEXTRON": "Textron", "NORTHROP": "Northrop Grumman", "BOEING": "Boeing",
    "L3HARRIS": "L3Harris", "LOCKHEED": "Lockheed Martin",
}

def post(payload):
    req = urllib.request.Request(
        API, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "uas-intel-brief/1.0"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode())

def fetch(keyword, start, end):
    body = {
        "filters": {
            "keywords": [keyword],
            "award_type_codes": ["A", "B", "C", "D"],
            "time_period": [{"start_date": start, "end_date": end}],
        },
        "fields": ["Award ID", "Recipient Name", "Award Amount", "Start Date",
                   "Awarding Agency", "Awarding Sub Agency", "Description",
                   "Place of Performance State Code", "generated_internal_id"],
        "page": 1, "limit": 60, "sort": "Award Amount", "order": "desc", "subawards": False,
    }
    try:
        return post(body).get("results", [])
    except Exception as e:
        print("query failed:", keyword, e)
        return []

def money(v):
    try: v = float(v)
    except (TypeError, ValueError): return "value n/a"
    if v >= 1e9:  return f"${v/1e9:.2f}B"
    if v >= 1e6:  return f"${v/1e6:.1f}M"
    if v >= 1e3:  return f"${v/1e3:.0f}K"
    return f"${v:.0f}"

def competitor(name):
    u = (name or "").upper()
    for k, label in COMPETITORS.items():
        if k in u: return label
    return None

def why(rec):
    """Template lenses. Emits a clause ONLY where notable. Silent otherwise."""
    out = []
    try: amt = float(rec.get("Award Amount") or 0)
    except (TypeError, ValueError): amt = 0
    text = f"{rec.get('Description','')} {rec.get('Award ID','')}"
    comp = competitor(rec.get("Recipient Name"))

    if comp:
        out.append(f"{comp} holds this scope")
    if amt >= 5e8:
        out.append("program-of-record scale")
    elif amt >= 5e7:
        out.append("major-program scale")
    if re.search(r"maritime|littoral|naval|carrier", text, re.I):
        out.append("maritime ISR capability area")
    if re.search(r"sustain|maintenance|logistics|spares|repair", text, re.I):
        out.append("sustainment vehicle, recurring revenue profile")
    if re.search(r"IDIQ|indefinite delivery|BPA|ordering agreement", text, re.I):
        out.append("IDIQ ceiling — on-ramp opportunities may follow")
    if re.search(r"ground control station|GCS|datalink|C2", text, re.I):
        out.append("ground segment adjacency")
    if re.search(r"prototype|OTA|research|development|SBIR", text, re.I):
        out.append("early-phase, capability shaping")
    return "; ".join(out[:2])

# ---------------- run ----------------
state = json.loads(STATE.read_text()) if STATE.exists() else {"runs": 0, "seen": []}
state["runs"] = state.get("runs", 0) + 1
seen = set(state.get("seen", []))
first_run = len(seen) == 0

now = datetime.datetime.now(datetime.timezone.utc)
window = 30 if first_run else 7
start = (now - datetime.timedelta(days=window)).strftime("%Y-%m-%d")
end = now.strftime("%Y-%m-%d")

found = {}
for q in QUERIES:
    for r in fetch(q, start, end):
        blob = f"{r.get('Description','')} {r.get('Award ID','')} {r.get('Awarding Sub Agency','')}"
        if not RELEVANT.search(blob):
            continue
        key = r.get("generated_internal_id") or r.get("Award ID")
        if key: found[key] = r

items = sorted(found.values(), key=lambda r: float(r.get("Award Amount") or 0), reverse=True)
new_ids = [k for k in found if k not in seen]
state["seen"] = list(seen | set(found.keys()))[-4000:]
state["last_run"] = now.strftime("%Y-%m-%d %H:%M UTC")
STATE.write_text(json.dumps(state, indent=2))

rows = []
for r in items[:60]:
    key = r.get("generated_internal_id") or r.get("Award ID")
    is_new = key in new_ids and not first_run
    parts = [
        r.get("Awarding Sub Agency") or r.get("Awarding Agency") or "Agency n/a",
        (r.get("Recipient Name") or "recipient n/a").title(),
        (r.get("Description") or "no description").strip()[:110],
        money(r.get("Award Amount")),
        r.get("Start Date") or "",
        r.get("Place of Performance State Code") or "",
    ]
    line = " &mdash; ".join(html.escape(p) for p in parts if p)
    clause = why(r)
    if clause:
        line += f' <span class="w">&mdash; {html.escape(clause)}</span>'
    flag = '<span class="new">NEW</span> ' if is_new else ""
    cls = "row comp" if competitor(r.get("Recipient Name")) else "row"
    rows.append(f'<div class="{cls}">{flag}{line}</div>')

comp_count = sum(1 for r in items if competitor(r.get("Recipient Name")))

TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>UAS DAILY INTELLIGENCE BRIEF</title>
<style>
 :root{--bg:#0a0d10;--fg:#e8edf2;--dim:#7c8a99;--accent:#00e08a;--rule:#1c242c;--amber:#ffb020;}
 *{box-sizing:border-box}
 body{margin:0;background:var(--bg);color:var(--fg);
   font:14px/1.55 "SF Mono",Consolas,"Roboto Mono",monospace;padding:36px 44px}
 header{border-bottom:2px solid var(--accent);padding-bottom:16px;margin-bottom:24px}
 h1{font-size:21px;letter-spacing:.18em;margin:0 0 14px;font-weight:600}
 .bar{display:flex;gap:44px;flex-wrap:wrap}
 .k{color:var(--dim);letter-spacing:.09em;font-size:10px;display:block;margin-bottom:2px}
 .v{color:var(--accent);font-size:20px;font-weight:600}
 h2{font-size:11px;letter-spacing:.16em;color:var(--dim);margin:30px 0 10px;font-weight:600}
 .row{padding:7px 0;border-bottom:1px solid var(--rule)}
 .row.comp{border-left:2px solid var(--amber);padding-left:11px}
 .w{color:var(--dim);font-style:italic}
 .new{color:var(--accent);font-size:10px;letter-spacing:.1em;
   border:1px solid var(--accent);padding:1px 5px;margin-right:7px}
 .note{color:var(--dim);font-size:11.5px;border-top:1px solid var(--rule);
   margin-top:32px;padding-top:14px;line-height:1.7}
</style></head><body>
<header><h1>UAS DAILY INTELLIGENCE BRIEF</h1>
<div class="bar">
 <div><span class="k">LAST UPDATED</span><span class="v">__NOW__</span></div>
 <div><span class="k">AUTONOMOUS RUNS</span><span class="v">__RUNS__</span></div>
 <div><span class="k">AWARDS TRACKED / __WIN__D</span><span class="v">__COUNT__</span></div>
 <div><span class="k">COMPETITOR ACTIONS</span><span class="v">__COMP__</span></div>
</div></header>
<h2>AWARDED CONTRACTS &mdash; UAS / ISR</h2>
__ROWS__
<p class="note">
Source: USAspending.gov API (federal awards). Awards are <b>executed contracts</b>, not open
solicitations, and reporting lags several weeks &mdash; this is a rear-view feed of where money
has already moved. Open solicitations (SAM.gov) attach once API credentials are issued.<br>
Relevance filtering is a keyword and agency heuristic; federal award data carries no
UAS-platform tag, so inclusion is approximate. Why-it-matters clauses are deterministic
rules over award fields, not model-generated.<br>
Amber rule = tracked competitor. Runs unattended on GitHub Actions every 6 hours.
</p></body></html>
"""

out = (TEMPLATE
   .replace("__NOW__", now.strftime("%Y-%m-%d %H:%M UTC"))
   .replace("__RUNS__", str(state["runs"]))
   .replace("__COUNT__", str(len(items)))
   .replace("__COMP__", str(comp_count))
   .replace("__WIN__", str(window))
   .replace("__ROWS__", "\n".join(rows) or '<div class="row">No matching awards in window.</div>'))
(DOCS / "index.html").write_text(out, encoding="utf-8")
print(f"run {state['runs']}: {len(items)} items, {len(new_ids)} new, {comp_count} competitor")
