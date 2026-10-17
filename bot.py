import os, json, requests, feedparser
from datetime import datetime
from PIL import Image

# ========= CONFIG - FREE ONLY - NO API-FOOTBALL =========
PAGE_ID = os.getenv("FB_PAGE_ID")
TOKEN = os.getenv("FB_TOKEN")
STATE_FILE = "posted_state.json"

NON_FOOTBALL = ["usyk","boxing","mcilroy","golf","tennis","f1","nba","rugby","cricket","ufc","bad light"]
# FREE ESPN LEAGUES
LEAGUES = ["eng.1","esp.1","ger.1","ita.1","fra.1","uefa.champions","uefa.europa","eng.2","ken.1"]

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
        r = requests.get(image_url, timeout=10, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code != 200:
            print(f"Image download failed {r.status_code}")
            return False
        with open("temp.jpg","wb") as f: f.write(r.content)
        # Fast check - clear & clean only
        try:
            if os.path.getsize("temp.jpg") < 15000:
                print("Image too small, skip")
                return False
        except: pass
        with open("temp.jpg","rb") as img_file:
            url = f"https://graph.facebook.com/{PAGE_ID}/photos"
            resp = requests.post(url, data={"caption":caption,"access_token":TOKEN}, files={"source":img_file}, timeout=20)
        print(f"FB PHOTO {resp.status_code} {resp.text[:200]}")
        return resp.status_code == 200
    except Exception as e:
        print(f"Photo error {e}")
        return False

def post_text(text):
    try:
        url = f"https://graph.facebook.com/{PAGE_ID}/feed"
        resp = requests.post(url, data={"message":text,"access_token":TOKEN}, timeout=15)
        print(f"FB TEXT {resp.status_code} {resp.text[:200]}")
        return resp.status_code == 200
    except Exception as e:
        print(f"Text post error {e}")
        return False

# ========= 1. LIVE SCORES - FAST - EVERY EVENT - FREE =========
live_posted = 0
print(f"--- CHECKING LIVE SCORES {datetime.now()} ---")
for league_code in LEAGUES:
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/scoreboard"
        data = requests.get(url, timeout=10).json()
        events = data.get("events", [])
        if len(events) > 0:
            print(f"LEAGUE {league_code}: {len(events)} games")
        for ev in events:
            try:
                comp = ev["competitions"][0]
                status_state = ev["status"]["type"]["state"] # pre, in, post
                status_detail = ev["status"]["type"]["name"] # STATUS_SCHEDULED, STATUS_IN_PROGRESS, etc
                minute = ev["status"].get("displayClock","")
                short_detail = ev["status"]["type"].get("shortDetail","")

                competitors = comp["competitors"]
                home = next((c for c in competitors if c["homeAway"]=="home"), competitors[0])
                away = next((c for c in competitors if c["homeAway"]=="away"), competitors[1])
                home_name = home["team"]["displayName"]
                away_name = away["team"]["displayName"]
                home_score = home.get("score","0")
                away_score = away.get("score","0")
                home_logo = home["team"].get("logo","")
                league_name = data["leagues"][0]["name"] if "leagues" in data else league_code
                league_logo = data["leagues"][0]["logos"][0]["href"] if data.get("leagues") and data["leagues"][0].get("logos") else home_logo
                ev_id = ev["id"]
                score_str = f"{home_name} {home_score}-{away_score} {away_name}"

                # KICK-OFF
                k_key = f"{ev_id}_KICK"
                if status_state == "in" and k_key not in state:
                    cap = f"🟢 KICK-OFF! LIVE NOW\n\n{home_name} vs {away_name}\n🏆 {league_name}\n⏱️ {short_detail}\n\nWho will win? Predict below 👇\n\nFOLLOW for LIVE GOALS + KPL!"
                    if post_with_photo(cap, league_logo or home_logo):
                        state[k_key] = True
                        live_posted += 1
                        save_state(state)

                # GOAL - DETECT EVERY SCORE CHANGE
                g_key = f"{ev_id}_GOAL_{home_score}_{away_score}"
                if status_state == "in" and g_key not in state:
                    # Only post if score > 0-0 (to avoid 0-0 kickoff)
                    if not (home_score=="0" and away_score=="0"):
                        cap = f"⚽ GOAL! {minute or short_detail}\n\n{score_str}\n🏆 {league_name}\n⏱️ {minute or short_detail}\n\nIs the game over? 👇\n#LiveScore #{home_name.replace(' ','')} #Goal"
                        if post_with_photo(cap, league_logo or home_logo):
                            state[g_key] = True
                            live_posted += 1
                            save_state(state)

                # RED CARD - from details
                for det in comp.get("details",[]):
                    txt = (det.get("text","") + det.get("type",{}).get("text","")).lower()
                    if "red card" in txt:
                        r_key = f"{ev_id}_RED_{det['id']}"
                        if r_key not in state:
                            cap = f"🟥 RED CARD! {minute or short_detail}\n\n{score_str}\n🏆 {league_name}\n{det.get('text','')}\n\nGame changed! 👇"
                            if post_with_photo(cap, league_logo):
                                state[r_key] = True
                                live_posted += 1
                                save_state(state)

                # HALF TIME
                ht_key = f"{ev_id}_HT"
                if "HALFTIME" in status_detail and ht_key not in state:
                    cap = f"⏸️ HALF TIME\n\n{score_str}\n🏆 {league_name}\n\nThoughts on first half? 👇"
                    if post_text(cap):
                        state[ht_key] = True
                        live_posted += 1
                        save_state(state)

                # FULL TIME
                ft_key = f"{ev_id}_FT"
                if status_state == "post" and ft_key not in state:
                    cap = f"✅ FULL TIME\n\n{score_str}\n🏆 {league_name}\n⏱️ {short_detail}\n\nRate this match 1-10! 👇\n#FT #FootballNews"
                    if post_with_photo(cap, league_logo):
                        state[ft_key] = True
                        live_posted += 1
                        save_state(state)
            except Exception as e:
                print(f"Event parse error {e}")
                continue
    except Exception as e:
        print(f"League {league_code} fetch error {e}")
        continue

print(f"LIVE POSTED: {live_posted}")

# ========= 2. FOOTBALL NEWS ONLY - BBC RSS - REAL HD PHOTO =========
news_posted = 0
try:
    print("--- CHECKING BBC FOOTBALL NEWS ---")
    feed = feedparser.parse("http://feeds.bbci.co.uk/sport/football/rss.xml")
    for entry in feed.entries[:15]:
        title = entry.title
        link = entry.link
        low = title.lower()
        if any(x in low for x in NON_FOOTBALL):
            print(f"Blocked: {title}")
            continue
        n_key = f"NEWS_{link}"
        if n_key in state:
            continue
        # Get HD clear photo
        img_url = None
        if hasattr(entry,'media_thumbnail') and len(entry.media_thumbnail)>0:
            img_url = entry.media_thumbnail[0]['url'].replace("320x180","1024x576").replace("624x351","1024x576")
        elif hasattr(entry,'media_content') and len(entry.media_content)>0:
            img_url = entry.media_content[0]['url']
        
        if not img_url:
            continue

        cap = f"🟢 BREAKING FOOTBALL NEWS! 📰\n\n{title}\n\nSource: BBC Sport\n\nYour thoughts? 👇 Is this true?\n\n🔥 FOLLOW 🟢 - 24/7 Football News + LIVE Goals + KPL!\n#FootballNews #Breaking #EPL #KPL"
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
print(f"DONE POSTED {live_posted+news_posted} - SUCCESS V18 FREE FAST")
save_state(state)
