import os, json, requests, feedparser
from datetime import datetime

# ========= CONFIG V18.1 FREE - NO PAID API =========
PAGE_ID = os.getenv("FB_PAGE_ID")
TOKEN = os.getenv("FB_TOKEN")
STATE_FILE = "posted_state.json"

NON_FOOTBALL = ["usyk","boxing","mcilroy","golf","tennis","f1","formula 1","nba","rugby","cricket","ufc","bad light"]

# 20+ LEAGUES - FREE ESPN - NO API KEY
LEAGUES = [
    "eng.1",        # Premier League
    "esp.1",        # LaLiga
    "ger.1",        # Bundesliga
    "ita.1",        # Serie A
    "fra.1",        # Ligue 1
    "ned.1",        # Eredivisie
    "por.1",        # Portugal
    "sco.1",        # Scotland
    "bel.1",        # Belgium
    "tur.1",        # Turkey
    "eng.2",        # Championship
    "eng.3",        # League One
    "usa.1",        # MLS
    "bra.1",        # Brazil
    "mex.1",        # Liga MX
    "sau.1",        # Saudi Pro League
    "uefa.champions",      # Champions League
    "uefa.europa",         # Europa League
    "uefa.europa.conf",    # Conference League
    "caf.champions",       # CAF Champions
    "ken.1"                # KPL Kenya (if available on ESPN)
]

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE,'r') as f: return json.load(f)
        except: return {}
    return {}

def save_state(s):
    with open(STATE_FILE,'w') as f: json.dump(s,f)

state = load_state()

def post_with_photo(caption, image_url):
    try:
        headers = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        r = requests.get(image_url, timeout=15, headers=headers)
        # If image too small or fails, use HD Premier League logo fallback - CLEAR & CLEAN
        if r.status_code != 200 or len(r.content) < 8000:
            print(f"Image small/fail {len(r.content) if r.status_code==200 else r.status_code}, using HD fallback")
            image_url = "https://upload.wikimedia.org/wikipedia/en/f/f2/Premier_League_Logo.svg.png"
            r = requests.get(image_url, timeout=10, headers=headers)
            if r.status_code != 200:
                image_url = "https://ichef.bbci.co.uk/ace/standard/1024/cpsprodpb/bbc_sport_logo.png"
                r = requests.get(image_url, timeout=10, headers=headers)

        with open("temp.jpg","wb") as f: f.write(r.content)
        
        with open("temp.jpg","rb") as img_file:
            url = f"https://graph.facebook.com/{PAGE_ID}/photos"
            resp = requests.post(url, data={"caption":caption,"access_token":TOKEN}, files={"source":img_file}, timeout=25)
        print(f"FB PHOTO {resp.status_code} {resp.text[:400]}")
        return resp.status_code == 200
    except Exception as e:
        print(f"Photo error {e}")
        return False

def post_text(text):
    try:
        url = f"https://graph.facebook.com/{PAGE_ID}/feed"
        resp = requests.post(url, data={"message":text,"access_token":TOKEN}, timeout=15)
        print(f"FB TEXT {resp.status_code} {resp.text[:300]}")
        return resp.status_code == 200
    except Exception as e:
        print(f"Text error {e}")
        return False

# ========= 1. LIVE SCORES - FAST - POST EVERYTHING =========
live_posted = 0
print(f"--- V18.1 FREE FAST {datetime.now()} CHECKING {len(LEAGUES)} LEAGUES ---")

for league_code in LEAGUES:
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/scoreboard"
        data = requests.get(url, timeout=10).json()
        events = data.get("events", [])
        if events:
            print(f"LEAGUE {league_code}: {len(events)} games")
        
        for ev in events:
            try:
                comp = ev["competitions"][0]
                status_state = ev["status"]["type"]["state"] # pre, in, post
                status_name = ev["status"]["type"]["name"]
                short_detail = ev["status"]["type"].get("shortDetail","")
                display_clock = ev["status"].get("displayClock","")

                competitors = comp["competitors"]
                home = next((c for c in competitors if c["homeAway"]=="home"), competitors[0])
                away = next((c for c in competitors if c["homeAway"]=="away"), competitors[1])

                home_name = home["team"]["displayName"]
                away_name = away["team"]["displayName"]
                home_score = home.get("score","0")
                away_score = away.get("score","0")
                home_logo = home["team"].get("logo","")
                away_logo = away["team"].get("logo","")

                league_name = data["leagues"][0]["name"] if data.get("leagues") else league_code
                league_logo = data["leagues"][0]["logos"][0]["href"] if data.get("leagues") and data["leagues"][0].get("logos") else home_logo

                ev_id = ev["id"]
                score_str = f"{home_name} {home_score}-{away_score} {away_name}"
                minute_str = display_clock or short_detail

                # --- KICK OFF ---
                k_key = f"{ev_id}_KICK"
                if status_state == "in" and k_key not in state:
                    cap = f"🟢 KICK-OFF! LIVE NOW\n\n{home_name} vs {away_name}\n🏆 {league_name}\n⏱️ {minute_str}\n\nLineups out! Who wins? 👇 Predict score!\n\nFOLLOW for LIVE GOALS + FOOTBALL NEWS + KPL!"
                    if post_with_photo(cap, league_logo or home_logo):
                        state[k_key] = True
                        live_posted += 1
                        save_state(state)

                # --- GOAL - EVERY SCORE CHANGE ---
                g_key = f"{ev_id}_GOAL_{home_score}_{away_score}"
                if status_state == "in" and g_key not in state:
                    if not (home_score=="0" and away_score=="0"):
                        cap = f"⚽ GOAL! {minute_str}\n\n{score_str}\n🏆 {league_name}\n⏱️ {minute_str}\n\nIs this game over? 👇 Comment!\n#LiveScore #Goal #Football"
                        if post_with_photo(cap, league_logo or home_logo):
                            state[g_key] = True
                            live_posted += 1
                            save_state(state)

                # --- RED CARD ---
                for det in comp.get("details",[]):
                    txt = (det.get("text","") + " " + det.get("type",{}).get("text","")).lower()
                    if "red card" in txt or "red-card" in txt:
                        r_key = f"{ev_id}_RED_{det.get('id','')}"
                        if r_key not in state:
                            cap = f"🟥 RED CARD! {minute_str}\n\n{score_str}\n🏆 {league_name}\n{det.get('text','Red Card')}\n\nGame changed! 👇"
                            if post_with_photo(cap, league_logo):
                                state[r_key] = True
                                live_posted += 1
                                save_state(state)

                # --- HALF TIME ---
                ht_key = f"{ev_id}_HT"
                if "HALFTIME" in status_name and ht_key not in state:
                    cap = f"⏸️ HALF TIME\n\n{score_str}\n🏆 {league_name}\n\nThoughts on first half? 👇"
                    if post_text(cap):
                        state[ht_key] = True
                        live_posted += 1
                        save_state(state)

                # --- FULL TIME ---
                ft_key = f"{ev_id}_FT"
                if status_state == "post" and ft_key not in state:
                    cap = f"✅ FULL TIME\n\n{score_str}\n🏆 {league_name}\n⏱️ {short_detail}\n\nRate this match 1-10! 👇 Who was MOTM?\n#FT #FootballNews #EPL #KPL"
                    if post_with_photo(cap, league_logo):
                        state[ft_key] = True
                        live_posted += 1
                        save_state(state)

            except Exception as e:
                print(f"Event error {e}")
                continue
    except Exception as e:
        print(f"League {league_code} error {e}")
        continue

print(f"LIVE POSTED: {live_posted}")

# ========= 2. FOOTBALL NEWS ONLY - BBC RSS - REAL HD PHOTO =========
news_posted = 0
try:
    print("--- CHECKING BBC FOOTBALL NEWS ---")
    feed = feedparser.parse("http://feeds.bbci.co.uk/sport/football/rss.xml")
    print(f"BBC found {len(feed.entries)} articles")
    for entry in feed.entries[:15]:
        title = entry.title
        link = entry.link
        low = title.lower()
        if any(x in low for x in NON_FOOTBALL):
            print(f"Blocked non-football: {title}")
            continue
        n_key = f"NEWS_{link}"
        if n_key in state:
            continue
        
        # Get HD clear photo - upgrade to 1024
        img_url = None
        if hasattr(entry,'media_thumbnail') and entry.media_thumbnail:
            img_url = entry.media_thumbnail[0]['url']
            img_url = img_url.replace("240x135","1024x576").replace("320x180","1024x576").replace("624x351","1024x576")
        if not img_url and hasattr(entry,'media_content') and entry.media_content:
            img_url = entry.media_content[0]['url']
        if not img_url:
            img_url = "https://upload.wikimedia.org/wikipedia/commons/7/7c/Premier_League_logo.png"

        cap = f"🟢 BREAKING FOOTBALL NEWS! 📰\n\n{title}\n\nSource: BBC Sport\nRead more: {link}\n\nYour thoughts? 👇 Is this true?\n\n🔥 FOLLOW 🟢 - 24/7 Football News + LIVE Goals + KPL + UCL!\n#FootballNews #Breaking #EPL #KPL #UCL"
        if post_with_photo(cap, img_url):
            state[n_key] = True
            news_posted += 1
            save_state(state)
            print(f"NEWS POSTED: {title}")
            if news_posted >= 2:
                break
except Exception as e:
    print(f"News error {e}")

print(f"NEWS POSTED: {news_posted}")
print(f"DONE POSTED {live_posted+news_posted} - SUCCESS V18.1 FREE FAST ALL LEAGUES")
save_state(state)
