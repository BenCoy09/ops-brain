#!/usr/bin/env python3
import os, json, time, subprocess, urllib.request, urllib.parse, uuid
from datetime import datetime, timezone

PROJECT = os.environ["SANITY_PROJECT_ID"]
DATASET = os.environ.get("SANITY_DATASET", "production")
TOKEN = os.environ["SANITY_TOKEN"]
API = f"https://{PROJECT}.api.sanity.io/v2025-02-19"

WATCH = ["nginx"]                      # services to monitor
ALLOWED_ACTIONS = {"restart_service"}  # the ONLY thing the agent may do
ALLOWED_SERVICES = set(WATCH)

def now():
    return datetime.now(timezone.utc).isoformat()

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)

def req(url, body=None):
    data = json.dumps(body).encode() if body else None
    r = urllib.request.Request(url, data=data, headers={
        "Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=30) as resp:
        return json.load(resp)

def query(groq):
    return req(f"{API}/data/query/{DATASET}?" + urllib.parse.urlencode({"query": groq}))["result"]

def mutate(mutations):
    return req(f"{API}/data/mutate/{DATASET}", {"mutations": mutations})

def is_active(svc):
    return run(["systemctl", "is-active", svc]).returncode == 0

def diagnose(svc, log):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return f"{svc} is not running. Logs suggest it stopped or crashed. Restart is low risk."
    body = {"model": "claude-sonnet-5-5", "max_tokens": 300, "messages": [{
        "role": "user",
        "content": f"Linux service {svc} is down. Recent logs:\n{log}\n\n"
                   "In 2-3 sentences: likely cause, and is a restart safe?"}]}
    r = urllib.request.Request("https://api.anthropic.com/v1/messages",
        data=json.dumps(body).encode(),
        headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return json.load(resp)["content"][0]["text"]
    except Exception as e:
        return f"(LLM unavailable: {e}) {svc} is down; restart proposed."

def detect():
    for svc in WATCH:
        if is_active(svc):
            continue
        open_count = query(f'count(*[_type=="incident" && service=="{svc}" '
                           f'&& status in ["awaiting_approval","approved"]])')
        if open_count:
            continue
        log = run(["journalctl", "-u", svc, "-n", "15", "--no-pager"]).stdout[-2000:]
        mutate([{"create": {
            "_id": "incident-" + uuid.uuid4().hex[:8], "_type": "incident",
            "title": f"{svc} is down", "service": svc,
            "status": "awaiting_approval", "logExcerpt": log,
            "diagnosis": diagnose(svc, log), "action": "restart_service",
            "risk": "low", "detectedAt": now()}}])
        print(f"[detected] {svc} down -> incident created")

def execute():
    rows = query('*[_type=="incident" && status=="approved"]{_id,service,action}')
    for row in rows:
        if row["action"] in ALLOWED_ACTIONS and row["service"] in ALLOWED_SERVICES:
            res = run(["systemctl", "restart", row["service"]])
            time.sleep(3)
            healthy = is_active(row["service"])
            out = (res.stdout + res.stderr).strip() or "restart issued"
        else:
            healthy, out = False, "Blocked: not in allowlist"
        mutate([{"patch": {"id": row["_id"], "set": {
            "status": "verified" if healthy else "failed",
            "result": out, "resolvedAt": now()}}}])
        print(f"[executed] {row['service']} -> {'verified' if healthy else 'failed'}")

if __name__ == "__main__":
    print("Ops Brain running...")
    while True:
        try:
            detect()
            execute()
        except Exception as e:
            print("error:", e)
        time.sleep(10)
