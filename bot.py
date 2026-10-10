import os, requests, json, time, random
from datetime import datetime, timedelta

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
        r = requests.post(url, data={"message": msg, "access_token": TOKEN}, timeout=25)
        print(f"POST {r.status_code}: {msg[:100]}")
        return r.status_code == 200
    except Exception as e:
        print(f"FB ERR {e}"); return False

def get_live():
    try:
        r = requests.get("https://v3.football.api-sports.io/fixtures?live=all", headers=HEADERS, timeout=20)
        return r.json().get("response", [])
    except: return []

def get_events(fid):
    try:
        r = requests.get(f"https://v3.football.api-sports.io/fixtures/events?fixture={fid}", headers=HEADERS, timeout=20)
        return r.json().get("response", [])
    except: return []

def get_lineups(fid):
    try:
        r = requests.get(f"https://v3.football.api-sports.io/fixtures/lineups?fixture={fid}", headers=HEADERS, timeout=20)
        return r.json().get("response", [])
    except: return []

def get_stats(fid):
    try:
        r = requests.get(f"https://v3.football.api-sports.io/fixtures/statistics?fixture={fid}", headers=HEADERS, timeout=20)
        return r.json().get("response", [])
    except: return []

def get_today():
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        r = requests.get(f"https://v3.football.api-sports.io/fixtures?date={today}&league={KPL_ID}", headers=HEADERS, timeout=20)
        kpl = r.json().get("response", [])
        if kpl: return kpl
        r = requests.get(f"https://v3.football.api-sports.io/fixtures?date={today}", headers=HEADERS, timeout=20)
        return r.json().get("response", [])[:15]
    except: return []

def get_transfers_breaking():
    try:
        # Top transfers as breaking news
        r = requests.get(f"https://v3.football.api-sports.io/transfers?team=33", headers=HEADERS, timeout=20) # Man Utd as sample for global breaking
        data = r.json().get("response", [])
        if data: return random.choice(data[:5])
        return None
    except: return None

posted = load_posted()
print(f"V6 ULTIMATE BEAT ALL | Lineups+Transfers+Stats | {len(posted)}")
start = time.time()
idle = 0

while True:
    if time.time()-start > 340*60:
        save_posted(posted); break

    games = get_live()
    games = sorted(games, key=lambda x: 0 if x['league']['id']==KPL_ID else 1)
    print(f"Live: {len(games)} | Idle: {idle}")

    if games:
        idle = 0
        for g in games[:15]:
            fid = g['fixture']['id']
            minute = g['fixture']['status']['elapsed'] or 0
            short = g['fixture']['status']['short']
            home = g['teams']['home']['name']; away = g['teams']['away']['name']
            hg = g['goals']['home'] or 0; ag = g['goals']['away'] or 0
            league = g['league']['name']; is_kpl = g['league']['id']==KPL_ID

            # 1. LINE-UPS — POST 1 HOUR BEFORE KICK
            if short in ["NS","TBD"]:
                lup_key = f"LINEUP-{fid}"
                if lup_key not in posted:
                    lineups = get_lineups(fid)
                    if lineups and len(lineups)==2:
                        msg = f"""📋 LINE-UPS — {league}
{home} vs {away}
⏰ Kickoff soon!

{home}:
{', '.join([p['player']['name'] for p in lineups[0]['startXI'][:5]])}...

{away}:
{', '.join([p['player']['name'] for p in lineups[1]['startXI'][:5]])}...

Full XI in comments 👇 Who wins?

#UnfilteredScores #LineUps #KPL"""
                        if post_fb(msg): posted.add(lup_key); save_posted(posted)

            # 2. GOALS / RED CARDS
            events = get_events(fid)
            for ev in events[-5:]:
                ev_key = f"{fid}-{ev['time']['elapsed']}-{ev['type']}-{ev['player']['id']}-{ev['detail']}"
                if ev_key in posted: continue
                if ev['type'] == 'Goal':
                    scorer = ev['player']['name']
                    badge = "🇰🇪 KPL" if is_kpl else "🌍"
                    dtype = "🎯 PENALTY!" if "penalty" in ev['detail'].lower() else "⚠️ OWN GOAL!" if "own" in ev['detail'].lower() else "⚽ GOAL!"
                    msg = f"""🟢 GOOOOAL!!! {badge} {minute}' — {league}
{dtype}
{scorer} ({ev['team']['name']})
{home} {hg} - {ag} {away}

Nani atashinda? 👇🔥 #UnfilteredScores"""
                    if post_fb(msg): posted.add(ev_key); save_posted(posted)
                elif ev['type'] == 'Card' and 'red' in ev['detail'].lower():
                    msg = f"""🟥 RED CARD! {minute}' — {league}
{ev['player']['name']} OFF!
{home} {hg} - {ag} {away} 😱 #UnfilteredScores"""
                    if post_fb(msg): posted.add(ev_key); save_posted(posted)

            # 3. FT + STATS + "INTERVIEW" STYLE POST-MATCH
            ft_key = f"FT-{fid}-{hg}-{ag}"
            if ft_key not in posted and short=="FT":
                stats = get_stats(fid)
                stat_text = ""
                if stats:
                    try:
                        h_stats = {s['type']:s['value'] for s in stats[0]['statistics']}
                        a_stats = {s['type']:s['value'] for s in stats[1]['statistics']}
                        stat_text = f"\n📊 Possession {h_stats.get('Ball Possession','-')} - {a_stats.get('Ball Possession','-')}\nShots {h_stats.get('Total Shots','-')} - {a_stats.get('Total Shots','-')}"
                    except: pass

                msg = f"""✅ FULL-TIME — {league}
{home} {hg} - {ag} {away}
{stat_text}

🗣️ POST-MATCH REACTION:
What did you think? Who was MOTM? Drop your rating 👇🔥

Full analysis on Unfiltered Scores! 🟢
#UnfilteredScores #KPL #FT"""

                if post_fb(msg): posted.add(ft_key); save_posted(posted)

    else:
        idle += 1
        if idle % 90 == 0: # Every ~50 mins when no live
            # ROTATE: Fixture / Transfer Breaking / Engagement
            choice = random.choice(['fixture','transfer','eng'])

            if choice == 'transfer':
                tr = get_transfers_breaking()
                if tr:
                    k = f"TR-{tr['player']['id']}-{datetime.now().strftime('%Y-%m-%d-%H')}"
                    if k not in posted:
                        msg = f"""🚨 BREAKING TRANSFER!

{tr['player']['name']} — {tr['transfers'][0]['type']}
{tr['transfers'][0]['teams']['in']['name']} ⬅️ {tr['transfers'][0]['teams']['out']['name']}

Rate this signing 👇🔥
#UnfilteredScores #Transfers #Breaking"""

                        if post_fb(msg): posted.add(k); save_posted(posted)

            else:
                todays = get_today()
                if todays:
                    g = random.choice(todays)
                    home = g['teams']['home']['name']; away = g['teams']['away']['name']
                    if g['fixture']['status']['short']=="NS":
                        k = f"FIX-{g['fixture']['id']}"
                        if k not in posted:
                            msg = f"""📅 TODAY — {g['league']['name']}
{home} vs {away}
⏰ {g['fixture']['date'][11:16]} EAT

Who wins? Predict! #UnfilteredScores"""
                            if post_fb(msg): posted.add(k); save_posted(posted)

    time.sleep(35)
