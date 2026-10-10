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
STATE_FILE = "posted_events.json" # GitHub will keep it if you commit

# --- FACEBOOK BOLD HACK ---
def bold(text):
    """Convert to unicode bold - works on Facebook"""
    normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    b = "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"
    res = ""
    for c in text:
        if c in normal:
            res += b[normal.index(c)]
        else:
            res += c
    return res

def fb_post(message):
    if not FB_TOKEN:
        print("No FB token")
        return False
    url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed"
    r = requests.post(url, data={"message": message, "access_token": FB_TOKEN}, timeout=20)
    print(f"FB {r.status_code}: {r.text[:400]}")
    return r.status_code == 200

def api_get(endpoint, params):
    try:
        r = requests.get(f"{API_URL}{endpoint}", headers=headers, params=params, timeout=20)
        print(f"API {endpoint} {params} -> {r.status_code} | {r.headers.get('x-ratelimit-remaining')}")
        return r.json().get("response", [])
    except Exception as e:
        print(f"API error {e}")
        return []

def load_state():
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
    except: pass
    return {"events": [], "lineups": [], "ft": []}

def save_state(state):
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f)
    except: pass

def main():
    state = load_state()
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")

    # 1. GET LIVE FIXTURES
    live = api_get("/fixtures", {"live": "all"})
    print(f"Live count: {len(live)}")

    if not live:
        # If no live, try morning lineups / fixtures / transfers depending on hour
        eat_hour = (now.hour + 3) % 24

        if 7 <= eat_hour <= 10: # Morning fixtures + lineups
            fixtures = api_get("/fixtures", {"date": today})
            top_ids = [39,140,135,78,61,2,3]
            fixtures = [f for f in fixtures if f['league']['id'] in top_ids][:12]
            if fixtures:
                msg = f"{BRAND}\n{bold('TODAYS TOP FIXTURES')}\n"
                msg += f"{today} | {TAGLINE}\n━━━━━━━━━━━━━━\n\n"
                for f in fixtures:
                    home = bold(f['teams']['home']['name'])
                    away = bold(f['teams']['away']['name'])
                    t = f['fixture']['date'][11:16]
                    h = (int(t.split(':')[0]) + 3) % 24
                    msg += f"⚽ {home} vs {away}\n 🏆 {f['league']['name']} | 🕒 {h:02d}:{t[3:5]} EAT\n\n"
                msg += f"Lineups dropping 1 hour before KO!\n\n{HASHTAGS}"
                fb_post(msg)
                return

        elif 18 <= eat_hour <= 19: # Transfers
            trans = api_get("/transfers", {"date": today})[:5]
            if trans:
                msg = f"{BRAND}\n{bold('TRANSFER UPDATE')}\n━━━━━━━━━━━━━━\n\n"
                for t in trans[:5]:
                    player = bold(t['player']['name'])
                    msg += f"🔄 {player}\n {t['transfers'][0]['teams']['out']['name']} ➡️ {t['transfers'][0]['teams']['in']['name']}\n\n"
                msg += f"{TAGLINE} 🟢\n{HASHTAGS} #Transfers"
                fb_post(msg)
                return
        print("No live, off-hour, skip to save quota")
        return

    # 2. LIVE PROCESSING - EVERY GOAL / CARD / PENALTY / HT / FT
    for fixture in live[:10]: # process 10 max per run to save quota
        fid = fixture['fixture']['id']
        home = fixture['teams']['home']['name']
        away = fixture['teams']['away']['name']
        hg = fixture['goals']['home']
        ag = fixture['goals']['away']
        elapsed = fixture['fixture']['status']['elapsed']
        status = fixture['fixture']['status']['short']
        league = fixture['league']['name']

        # A) LINEUPS - 1 hour before
        if status == "NS" and fid not in state["lineups"]:
            lineups = api_get("/fixtures/lineups", {"fixture": fid})
            if lineups:
                msg = f"{BRAND}\n{bold('LINEUPS ARE IN!')}\n━━━━━━━━━━━━━━\n"
                msg += f"{bold(home)} vs {bold(away)}\n🏆 {league}\n\n"
                for team_data in lineups:
                    team = bold(team_data['team']['name'])
                    msg += f"{team} XI:\n"
                    for p in team_data['startXI'][:11]:
                        msg += f"• {p['player']['name']}\n"
                    msg += "\n"
                msg += f"{TAGLINE} 🟢\n{HASHTAGS} #Lineups"
                if fb_post(msg):
                    state["lineups"].append(fid)

        # B) EVENTS - Goals, Red Cards, Penalties
        events = api_get("/fixtures/events", {"fixture": fid})
        for ev in events:
            ev_id = f"{fid}-{ev['time']['elapsed']}-{ev['player']['id']}-{ev['type']}-{ev['detail']}"
            if ev_id in state["events"]:
                continue

            # GOAL
            if ev['type'] == 'Goal':
                msg = f"{BRAND}\n{bold('GOOOAL!!!')}\n━━━━━━━━━━━━━━\n"
                msg += f"{bold(home)} {hg} - {ag} {bold(away)}\n"
                msg += f"⚽ {bold(ev['player']['name'])} {ev['time']['elapsed']}'\n"
                if ev.get('assist'):
                    msg += f"🎯 Assist: {ev['assist']['name']}\n"
                msg += f"🏆 {league} | ⏱️ {elapsed}'\n\n{bold('LIVE')} on {TAGLINE} 🟢\n\n{HASHTAGS} #Goal"
                if fb_post(msg):
                    state["events"].append(ev_id)
                    save_state(state)
                    time.sleep(3)
                    return # Post 1 event per run to avoid spam + save quota

            # RED CARD
            if ev['detail'] == 'Red Card':
                msg = f"{BRAND}\n{bold('RED CARD! 🟥')}\n━━━━━━━━━━━━━━\n"
                msg += f"{bold(ev['player']['name'])} - {ev['team']['name']}\n"
                msg += f"{bold(home)} {hg} - {ag} {bold(away)} | {elapsed}'\n"
                msg += f"🏆 {league}\n\n{HASHTAGS}"
                if fb_post(msg):
                    state["events"].append(ev_id)
                    save_state(state)
                    return

            # PENALTY
            if 'Penalty' in ev['detail']:
                icon = "✅" if "Goal" in ev['detail'] or ev['type'] == 'Goal' else "❌"
                msg = f"{BRAND}\n{bold(f'PENALTY {ev['detail'].upper()}')} {icon}\n━━━━━━━━━━━━━━\n"
                msg += f"{bold(ev['player']['name'])} ({ev['team']['name']})\n"
                msg += f"{bold(home)} {hg} - {ag} {bold(away)} | {elapsed}'\n\n{HASHTAGS}"
                if fb_post(msg):
                    state["events"].append(ev_id)
                    save_state(state)
                    return

        # C) HT / FT
        if status == "HT" and f"ht-{fid}" not in state["events"]:
            msg = f"{BRAND}\n{bold('HALF TIME')}\n━━━━━━━━━━━━━━\n"
            msg += f"{bold(home)} {hg} - {ag} {bold(away)}\n🏆 {league}\n\nSecond half soon! 🟢\n\n{HASHTAGS} #HT"
            if fb_post(msg):
                state["events"].append(f"ht-{fid}")
                save_state(state)
                return

        if status == "FT" and fid not in state["ft"]:
            msg = f"{BRAND}\n{bold('FULL TIME')}\n━━━━━━━━━━━━━━\n"
            msg += f"{bold(home)} {hg} - {ag} {bold(away)}\n🏆 {league}\n\n"
            msg += f"{bold('FT Result')} | {TAGLINE} 🟢\n\n{HASHTAGS} #FT"
            if fb_post(msg):
                state["ft"].append(fid)
                save_state(state)
                return

    save_state(state)
    print("Done - no new events")

if __name__ == "__main__":
    main()
