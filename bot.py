import os, requests, json, time
from datetime import datetime, timezone, timedelta

BRAND = "🟢 Unfiltered Scores"
TAGLINE = "No Filters, Just Football"
HASHTAGS = "#UnfilteredScores #LiveFootball"
FB_PAGE_ID = os.getenv("FB_PAGE_ID", "61595099671352")
FB_TOKEN = os.getenv("FB_PAGE_TOKEN") or os.getenv("FB_TOKEN")
API_URL = os.getenv("API_URL", "https://v3.football.api-sports.io").rstrip("/")
API_KEY = os.getenv("API_KEY")
headers = {"x-apisports-key": API_KEY}
STATE_FILE = "posted_events.json"

def bold(text):
    normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    b = "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"
    res = ""
    for c in text:
        if c in normal: res += b[normal.index(c)]
        else: res += c
    return res

def fb_post(message):
    if not FB_TOKEN: return False
    url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed"
    r = requests.post(url, data={"message": message, "access_token": FB_TOKEN}, timeout=20)
    print(f"FB {r.status_code}: {r.text[:300]}")
    return r.status_code == 200

def api_get(endpoint, params):
    try:
        r = requests.get(f"{API_URL}{endpoint}", headers=headers, params=params, timeout=20)
        print(f"API {endpoint} -> {r.status_code} rem:{r.headers.get('x-ratelimit-remaining')}")
        return r.json().get("response", [])
    except Exception as e:
        print(f"API error {e}")
        return []

def load_state():
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f: return json.load(f)
    except: pass
    return {"events": [], "lineups": [], "ft": []}

def save_state(state):
    with open(STATE_FILE, 'w') as f: json.dump(state, f)

def main():
    state = load_state()
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")

    # 1. CHECK LINEUPS FOR UPCOMING GAMES (FIX FOR ARSENAL-LEEDS)
    fixtures_today = api_get("/fixtures", {"date": today})
    # Focus on top leagues + Arsenal game
    for f in fixtures_today:
        fid = f['fixture']['id']
        if fid in state["lineups"]: continue

        home = f['teams']['home']['name']
        away = f['teams']['away']['name']
        # Check if Arsenal vs Leeds or any top game
        is_target = ("Arsenal" in home or "Arsenal" in away or "Leeds" in home or "Leeds" in away or f['league']['id'] in [39,140,135,78,61])

        kickoff_str = f['fixture']['date'] # 2026-05-13T19:00:00+00:00
        kickoff = datetime.fromisoformat(kickoff_str.replace("Z","+00:00"))
        mins_to_ko = (kickoff - now).total_seconds() / 60

        # If game is in 5 to 75 mins -> check lineups
        if is_target and 5 < mins_to_ko < 75:
            print(f"Checking lineups for {home} vs {away} in {mins_to_ko:.0f} mins")
            lineups = api_get("/fixtures/lineups", {"fixture": fid})
            if lineups and len(lineups) >= 2 and lineups[0]['startXI']:
                msg = f"{BRAND}\n{bold('LINEUPS ARE IN!')}\n━━━━━━━━━━━━━━\n"
                msg += f"{bold(home)} vs {bold(away)}\n🏆 {f['league']['name']}\n🕒 KO: {kickoff.hour+3:02d}:{(kickoff.minute):02d} EAT\n\n"
                for team_data in lineups:
                    team = bold(team_data['team']['name'])
                    msg += f"{team} XI:\n"
                    for p in team_data['startXI'][:11]:
                        msg += f"• {p['player']['name']}\n"
                    msg += "\n"
                msg += f"{TAGLINE} 🟢\n{HASHTAGS} #Lineups #PL"
                if fb_post(msg):
                    state["lineups"].append(fid)
                    save_state(state)
                    return # Post one lineup at a time

    # 2. CHECK LIVE GOALS
    live = api_get("/fixtures", {"live": "all"})
    print(f"Live count: {len(live)}")

    if not live:
        print("No live games, done")
        save_state(state)
        return

    for fixture in live[:10]:
        fid = fixture['fixture']['id']
        home = fixture['teams']['home']['name']
        away = fixture['teams']['away']['name']
        hg = fixture['goals']['home']
        ag = fixture['goals']['away']
        elapsed = fixture['fixture']['status']['elapsed']
        status = fixture['fixture']['status']['short']
        league = fixture['league']['name']

        events = api_get("/fixtures/events", {"fixture": fid})
        for ev in events:
            ev_id = f"{fid}-{ev['time']['elapsed']}-{ev['player']['id']}-{ev['type']}-{ev['detail']}"
            if ev_id in state["events"]: continue
            if ev['type'] == 'Goal':
                msg = f"{BRAND}\n{bold('GOOOAL!!!')}\n━━━━━━━━━━━━━━\n{bold(home)} {hg} - {ag} {bold(away)}\n⚽ {bold(ev['player']['name'])} {ev['time']['elapsed']}'\n🏆 {league} | ⏱️ {elapsed}'\n\n{bold('LIVE')} on {TAGLINE} 🟢\n\n{HASHTAGS} #Goal"
                if fb_post(msg):
                    state["events"].append(ev_id)
                    save_state(state)
                    return
        if status == "HT" and f"ht-{fid}" not in state["events"]:
            msg = f"{BRAND}\n{bold('HALF TIME')}\n━━━━━━━━━━━━━━\n{bold(home)} {hg} - {ag} {bold(away)}\n🏆 {league}\n\n{HASHTAGS} #HT"
            if fb_post(msg):
                state["events"].append(f"ht-{fid}")
                save_state(state)
                return
        if status == "FT" and fid not in state["ft"]:
            msg = f"{BRAND}\n{bold('FULL TIME')}\n━━━━━━━━━━━━━━\n{bold(home)} {hg} - {ag} {bold(away)}\n🏆 {league}\n\n{HASHTAGS} #FT"
            if fb_post(msg):
                state["ft"].append(fid)
                save_state(state)
                return
    save_state(state)

if __name__ == "__main__":
    main()
