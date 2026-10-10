import os, requests, json, time, xml.etree.ElementTree as ET
from datetime import datetime

# ========== CONFIG ==========
API_KEY = os.getenv("API_KEY") or os.getenv("API_FOOTBALL_KEY")
PAGE_ID = os.getenv("FB_PAGE_ID")
TOKEN = os.getenv("FB_PAGE_TOKEN") or os.getenv("FB_TOKEN")
HEADERS = {"x-apisports-key": API_KEY}

BRAND = "🟢" # YOUR GLOBAL BRAND
TAG = "#UnfilteredScores 🟢"
TOP_LEAGUES = [39, 140, 135, 78, 61, 2, 3, 848] # EPL, LaLiga, SerieA, Bundesliga, Ligue1, UCL, UEL, ECL
KPL_ID = 277 # Keep for future, not used now

# ========== STORAGE ==========
def load_posted():
    try:
        with open("posted.json","r") as f: return set(json.load(f))
    except: return set()

def save_posted(p):
    with open("posted.json","w") as f: json.dump(list(p), f)

def post_fb(msg):
    if not msg.startswith(BRAND): msg = f"{BRAND} {msg}"
    try:
        url = f"https://graph.facebook.com/v20.0/{PAGE_ID}/feed"
        r = requests.post(url, data={"message": msg, "access_token": TOKEN}, timeout=25)
        print(f"POST {r.status_code}: {msg[:130]} | {r.text[:200]}")
        return r.status_code == 200
    except Exception as e:
        print(f"FB ERR {e}"); return False

# ========== API FETCHERS ==========
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
        r = requests.get(f"https://v3.football.api-sports.io/fixtures?date={today}", headers=HEADERS, timeout=20)
        games = r.json().get("response", [])
        return sorted(games, key=lambda x: 0 if x['league']['id'] in TOP_LEAGUES else 1)[:25]
    except: return []

def get_verified_news():
    """BBC Sport Football - 100% verified"""
    try:
        r = requests.get("https://feeds.bbci.co.uk/sport/football/rss.xml?edition=uk", timeout=15, headers={"User-Agent":"Mozilla/5.0"})
        root = ET.fromstring(r.content)
        news = []
        for item in root.findall('.//item')[:20]:
            title = item.find('title').text if item.find('title') is not None else ""
            desc = item.find('description').text if item.find('description') is not None else ""
            if title and len(title) > 25:
                news.append({"title": title.strip(), "desc": desc.strip()[:180]})
        print(f"VERIFIED NEWS: {len(news)}")
        return news
    except Exception as e:
        print(f"NEWS ERR {e}"); return []

def get_transfer_breaking():
    """Real transfers as breaking news"""
    try:
        # Try multiple big teams to get fresh transfer
        for team_id in [33, 49, 50, 40, 42]: # ManUtd, Chelsea, ManCity, Liverpool, Arsenal
            r = requests.get(f"https://v3.football.api-sports.io/transfers?team={team_id}", headers=HEADERS, timeout=15)
            data = r.json().get("response", [])
            if data:
                return data[0]
        return None
    except: return None

# ========== MAIN LOOP ==========
posted = load_posted()
print(f"{BRAND} V7 GLOBAL NO.1 FINAL | EVERYTHING | Memory {len(posted)}")
start = time.time()
idx = 0
first_post_done = False

while True:
    if time.time() - start > 340*60: # 5h40m stable
        save_posted(posted); break

    games = get_live()
    games = sorted(games, key=lambda x: 0 if x['league']['id'] in TOP_LEAGUES else 1)
    print(f"Live: {len(games)} | Idx: {idx} | First: {first_post_done}")

    # ===== 1. LIVE MODE - GOALS, REDS, LINEUPS, HT/FT WITH STATS =====
    if games:
        first_post_done = True
        for g in games[:15]:
            fid = g['fixture']['id']
            minute = g['fixture']['status']['elapsed'] or 0
            short = g['fixture']['status']['short']
            home = g['teams']['home']['name']; away = g['teams']['away']['name']
            hg = g['goals']['home'] or 0; ag = g['goals']['away'] or 0
            league = g['league']['name']

            # LINE-UPS (when NS and lineups available)
            if short == "NS":
                lup_key = f"LINEUP-{fid}"
                if lup_key not in posted:
                    lineups = get_lineups(fid)
                    if lineups and len(lineups)==2:
                        h11 = ', '.join([p['player']['name'] for p in lineups[0]['startXI'][:6]])
                        a11 = ', '.join([p['player']['name'] for p in lineups[1]['startXI'][:6]])
                        msg = f"""{BRAND} LINE-UPS — {league}

{BRAND} {home}: {h11}...
{BRAND} {away}: {a11}...

Kickoff soon! Who wins? 👇

{TAG} #LineUps"""
                        if post_fb(msg): posted.add(lup_key); save_posted(posted)

            # GOALS + RED CARDS
            events = get_events(fid)
            for ev in events[-6:]:
                ev_key = f"{fid}-{ev['time']['elapsed']}-{ev['type']}-{ev['player']['id']}-{ev['detail']}"
                if ev_key in posted: continue

                if ev['type'] == 'Goal':
                    scorer = ev['player']['name']
                    team = ev['team']['name']
                    det = ev['detail'].lower()
                    dtype = "🎯 PENALTY!" if "penalty" in det else "⚠️ OWN GOAL!" if "own" in det else "⚽ GOAL!"
                    msg = f"""{BRAND} GOOOOAL!!! {minute}' — {league}
{BRAND} {dtype}

{scorer} ({team})
{home} {hg} - {ag} {away}

Who wins this? 👇🔥

{TAG} #Live"""
                    if post_fb(msg): posted.add(ev_key); save_posted(posted)

                elif ev['type'] == 'Card' and 'red' in ev['detail'].lower():
                    msg = f"""{BRAND} RED CARD! {minute}' — {league}

{BRAND} {ev['player']['name']} ({ev['team']['name']}) OFF!
{home} {hg} - {ag} {away}

Game changed completely! 😱

{TAG}"""
                    if post_fb(msg): posted.add(ev_key); save_posted(posted)

            # HALF-TIME / FULL-TIME + STATS + POST-MATCH "INTERVIEW"
            ft_key = f"STATUS-{fid}-{short}-{hg}-{ag}"
            if ft_key not in posted and short in ["HT","FT"]:
                stats_text = ""
                stats = get_stats(fid)
                if stats and len(stats)==2:
                    try:
                        h = {s['type']:s['value'] for s in stats[0]['statistics']}
                        a = {s['type']:s['value'] for s in stats[1]['statistics']}
                        stats_text = f"\n📊 Poss: {h.get('Ball Possession','-')} - {a.get('Ball Possession','-')} | Shots: {h.get('Total Shots','-')} - {a.get('Total Shots','-')} | On Target: {h.get('Shots on Goal','-')} - {a.get('Shots on Goal','-')}"
                    except: pass

                if short == "HT":
                    msg = f"""{BRAND} HALF-TIME — {league}
{BRAND} {home} {hg} - {ag} {away}
{stats_text}

Second half who wins? 👇

{TAG}"""
                else:
                    msg = f"""{BRAND} FULL-TIME — {league}
{BRAND} {home} {hg} - {ag} {away}
{stats_text}

{BRAND} POST-MATCH REACTION:
Who was MOTM? Rate the game! 👇🔥

{TAG} #FT"""

                if post_fb(msg): posted.add(ft_key); save_posted(posted)

    # ===== 2. NO LIVE MODE - VERIFIED NEWS + FIXTURES + TRANSFERS (NO RANDOM) =====
    else:
        todays = get_today()
        cycle = int(time.time()/1800) % 3 # Rotate every 30 mins

        if not first_post_done or cycle == 0:
            # TODAY FIXTURES
            if todays:
                g = todays[idx % len(todays)]
                k = f"FIX-{g['fixture']['id']}"
                if k not in posted:
                    home = g['teams']['home']['name']; away = g['teams']['away']['name']
                    league = g['league']['name']; kick = g['fixture']['date'][11:16]
                    status = g['fixture']['status']['short']
                    hg = g['goals']['home']; ag = g['goals']['away']

                    if status == "FT":
                        msg = f"""{BRAND} RESULT — {league}
{BRAND} {home} {hg} - {ag} {away}

Thoughts? 👇

{TAG}"""
                    else:
                        msg = f"""{BRAND} TODAY — {league}

{BRAND} {home} vs {away}
⏰ {kick} EAT

Who wins? Predict score! 👇🔥

{TAG}"""

                    if post_fb(msg):
                        posted.add(k); save_posted(posted)
                        idx += 1; first_post_done = True

        elif cycle == 1:
            # VERIFIED BBC NEWS
            news_list = get_verified_news()
            if news_list:
                for n in news_list:
                    nk = f"NEWS-{hash(n['title'])}"
                    if nk not in posted:
                        msg = f"""{BRAND} BREAKING — VERIFIED

{BRAND} {n['title']}

{n['desc']}

Source: BBC Sport {BRAND}

Your thoughts? 👇

{TAG} #FootballNews"""

                        if post_fb(msg):
                            posted.add(nk); save_posted(posted)
                            first_post_done = True
                            break

        else:
            # TRANSFER BREAKING
            tr = get_transfer_breaking()
            if tr:
                tk = f"TR-{tr['player']['id']}-{tr['transfers'][0]['date']}"
                if tk not in posted:
                    t = tr['transfers'][0]
                    msg = f"""{BRAND} TRANSFER — VERIFIED

{BRAND} {tr['player']['name']}
{t['teams']['out']['name']} ➡️ {t['teams']['in']['name']}
Type: {t['type']}

Rate this signing! 👇🔥

{TAG} #Transfers"""

                    if post_fb(msg):
                        posted.add(tk); save_posted(posted)
                        first_post_done = True

    time.sleep(35)
