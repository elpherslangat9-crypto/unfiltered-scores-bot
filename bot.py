import os, requests, json, time
from datetime import datetime

API_KEY = os.getenv("API_KEY") or os.getenv("API_FOOTBALL_KEY")
PAGE_ID = os.getenv("FB_PAGE_ID")
TOKEN = os.getenv("FB_PAGE_TOKEN") or os.getenv("FB_TOKEN")
HEADERS = {"x-apisports-key": API_KEY}
KPL_ID = 277

def load_posted():
    try:
        with open("posted.json","r") as f: return set(json.load(f))
    except: return set()

def save_posted(p):
    with open("posted.json","w") as f: json.dump(list(p), f)

def post_fb(msg):
    try:
        url = f"https://graph.facebook.com/v20.0/{PAGE_ID}/feed"
        r = requests.post(url, data={"message": msg, "access_token": TOKEN}, timeout=20)
        print(f"POST {r.status_code}: {msg[:80]} | {r.text[:200]}")
        return r.status_code == 200
    except Exception as e:
        print(f"FB ERR {e}"); return False

def get_live():
    try:
        r = requests.get("https://v3.football.api-sports.io/fixtures?live=all", headers=HEADERS, timeout=20)
        return r.json().get("response", [])
    except Exception as e:
        print(f"API ERR {e}"); return []

def get_events(fid):
    try:
        r = requests.get(f"https://v3.football.api-sports.io/fixtures/events?fixture={fid}", headers=HEADERS, timeout=20)
        return r.json().get("response", [])
    except: return []

posted = load_posted()
print(f"V3 TEXT-ONLY WORLD NO.1 | Memory {len(posted)} | KPL FIRST")

start = time.time()
while True:
    if time.time()-start > 340*60:
        save_posted(posted); break

    games = get_live()
    games = sorted(games, key=lambda x: 0 if x['league']['id']==KPL_ID else 1)
    print(f"Live: {len(games)}")

    for g in games[:15]:
        fid = g['fixture']['id']
        minute = g['fixture']['status']['elapsed'] or 0
        short = g['fixture']['status']['short']
        home = g['teams']['home']['name']
        away = g['teams']['away']['name']
        hg = g['goals']['home'] or 0
        ag = g['goals']['away'] or 0
        league = g['league']['name']
        is_kpl = g['league']['id']==KPL_ID

        events = get_events(fid)
        for ev in events[-4:]:
            ev_key = f"{fid}-{ev['time']['elapsed']}-{ev['type']}-{ev['player']['id']}-{ev['detail']}"
            if ev_key in posted: continue

            if ev['type'] == 'Goal':
                scorer = ev['player']['name']
                team = ev['team']['name']
                badge = "🇰🇪 KPL" if is_kpl else "🌍"
                msg = f"""🟢 GOOOOAL!!! {badge} {minute}' — {league}

⚽ {scorer} ({team})
{home} {hg} - {ag} {away}

Nani atashinda? Drop prediction 👇🔥

#UnfilteredScores #LiveScores #KPL #FootballKE"""

                if post_fb(msg):
                    posted.add(ev_key); save_posted(posted)
                    print(f"Who win {home} {hg}-{ag} {away} | Scorer {scorer}")

            elif ev['type'] == 'Card' and 'red' in ev['detail'].lower():
                msg = f"""🟥 RED CARD! {minute}' — {league}

{ev['player']['name']} ({ev['team']['name']}) sent OFF!

{home} {hg} - {ag} {away}
Game imebadilika! 😱

#UnfilteredScores #KPL"""

                if post_fb(msg):
                    posted.add(ev_key); save_posted(posted)

        ft_key = f"{fid}-{short}-{hg}-{ag}"
        if ft_key not in posted and short in ["HT","FT"]:
            title = "⏸️ HALF-TIME" if short=="HT" else "✅ FULL-TIME"
            msg = f"""{title} — {league}

{home} {hg} - {ag} {away}
⏱️ {minute}'

Follow Unfiltered Scores for next LIVE! 🟢
#UnfilteredScores"""
            if post_fb(msg):
                posted.add(ft_key); save_posted(posted)

    time.sleep(35)
