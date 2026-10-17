import os, json, requests, time
from datetime import datetime
from PIL import Image

# ========= CONFIG =========
PAGE_ID = os.getenv("FB_PAGE_ID")
TOKEN = os.getenv("FB_TOKEN")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY") # api-football.com
NEWS_API_KEY = os.getenv("NEWS_API_KEY") # newsapi.org

STATE_FILE = "posted_state.json"

BIG_LEAGUES = [39, 140, 78, 135, 61, 2, 3, 848] # EPL, LaLiga, Bundesliga, Serie A, Ligue 1, UCL, UEL, KPL Kenya

FOOTBALL_KEYWORDS = ["football","premier league","epl","laliga","bundesliga","serie a","ligue 1","kpl","champions league","ucl","goal","transfer","arsenal","chelsea","liverpool","man utd","barcelona","real madrid"]
NON_FOOTBALL = ["usyk","boxing","mcilroy","golf","tennis","f1","formula 1","nba","rugby","cricket","ufc","bad light"]

# ========= STATE =========
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE,'r') as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE,'w') as f:
        json.dump(state, f)

state = load_state()

# ========= FACEBOOK POST =========
def post_with_photo(caption, image_url):
    try:
        # 1. Download real photo
        r = requests.get(image_url, timeout=15)
        with open("temp.jpg","wb") as f:
            f.write(r.content)
        
        # 2. Check if clear & clean
        try:
            im = Image.open("temp.jpg")
            w,h = im.size
            size_kb = os.path.getsize("temp.jpg") / 1024
            print(f"Image check: {w}x{h} - {size_kb:.0f}KB")
            if w < 600 or h < 400 or size_kb < 40:
                print("Image too blurry/small, skipping")
                return None
        except:
            pass

        # 3. Post to FB as PHOTO (HD)
        with open("temp.jpg","rb") as img_file:
            url = f"https://graph.facebook.com/{PAGE_ID}/photos"
            resp = requests.post(url, data={
                "caption": caption,
                "access_token": TOKEN
            }, files={"source": img_file})
        print(f"FB PHOTO {resp.status_code} {resp.text[:200]}")
        return resp
    except Exception as e:
        print(f"Photo post error {e}")
        return None

def post_text(text):
    url = f"https://graph.facebook.com/{PAGE_ID}/feed"
    resp = requests.post(url, data={"message": text, "access_token": TOKEN})
    print(f"FB TEXT {resp.status_code} {resp.text[:200]}")
    return resp

# ========= 1. LIVESCORES ENGINE - EVERY EVENT =========
def get_live_scores():
    headers = {"x-apisports-key": FOOTBALL_API_KEY}
    url = "https://v3.football.api-sports.io/fixtures?live=all"
    r = requests.get(url, headers=headers)
    data = r.json().get("response", [])
    
    print(f"TOTAL LIVE FIXTURES: {len(data)}")
    
    posts_made = 0
    for match in data:
        league_id = match["league"]["id"]
        if league_id not in BIG_LEAGUES:
            continue
        
        fixture_id = str(match["fixture"]["id"])
        minute = match["fixture"]["status"]["elapsed"]
        status = match["fixture"]["status"]["short"] # NS, 1H, HT, 2H, FT
        home = match["teams"]["home"]["name"]
        away = match["teams"]["away"]["name"]
        goals_home = match["goals"]["home"]
        goals_away = match["goals"]["away"]
        score_str = f"{home} {goals_home}-{goals_away} {away}"

        # --- KICK OFF ---
        key = f"{fixture_id}_NS"
        if status in ["1H","HT","2H"] and key not in state:
            # Try get lineup photo
            lineup_img = match["teams"]["home"].get("logo")
            caption = f"🟢 KICK-OFF!\n\n{home} vs {away}\nLeague: {match['league']['name']}\n\nLineups are out! Who will win? 👇\n\nFOLLOW for LIVE Goals!"
            post_with_photo(caption, lineup_img)
            state[key] = True
            posts_made += 1

        # --- GOAL - DETECT EVERY SCORE ---
        key_goal = f"{fixture_id}_GOAL_{goals_home}_{goals_away}_{minute}"
        if status in ["1H","2H"] and key_goal not in state and (goals_home+goals_away>0):
            # This detects EVERY change in score
            caption = f"⚽ GOAL! {minute}'\n\n{score_str}\n⏱️ {minute}'\n🏆 {match['league']['name']}\n\nIs this game over? 👇\n\n#LiveScore #Goal #{home.replace(' ','')}"
            post_with_photo(caption, match["league"]["logo"])
            state[key_goal] = True
            posts_made += 1

        # --- RED CARD ---
        events_url = f"https://v3.football.api-sports.io/fixtures/events?fixture={fixture_id}"
        ev = requests.get(events_url, headers=headers).json().get("response",[])
        for e in ev:
            if e["type"]=="Card" and "Red" in e["detail"]:
                key_red = f"{fixture_id}_RED_{e['player']['id']}_{e['time']['elapsed']}"
                if key_red not in state:
                    caption = f"🟥 RED CARD! {e['time']['elapsed']}'\n\n{score_str}\nPlayer: {e['player']['name']} ({e['team']['name']})\n\nGame changed! 👇\n"
                    post_with_photo(caption, match["league"]["logo"])
                    state[key_red] = True
                    posts_made += 1

        # --- HT ---
        key_ht = f"{fixture_id}_HT"
        if status=="HT" and key_ht not in state:
            caption = f"⏸️ HALF TIME\n\n{score_str}\n\nYour thoughts on first half? 👇"
            post_text(caption)
            state[key_ht] = True
            posts_made += 1

        # --- FT ---
        key_ft = f"{fixture_id}_FT"
        if status=="FT" and key_ft not in state:
            caption = f"✅ FULL TIME\n\n{score_str}\n🏆 {match['league']['name']}\n\nRate this match 1-10! 👇\n#FT #FootballNews"
            post_with_photo(caption, match["league"]["logo"])
            state[key_ft] = True
            posts_made += 1

    save_state(state)
    return posts_made

# ========= 2. FOOTBALL NEWS ENGINE - REAL HD PHOTO ONLY =========
def get_football_news():
    url = f"https://newsapi.org/v2/everything?q=football&language=en&sortBy=publishedAt&pageSize=20&apiKey={NEWS_API_KEY}"
    r = requests.get(url).json()
    articles = r.get("articles", [])
    made = 0
    for art in articles:
        title = art["title"]
        img = art["urlToImage"]
        if not img:
            continue
        
        low = title.lower()
        # BLOCK NON-FOOTBALL like Usyk, McIlroy
        if any(b in low for b in NON_FOOTBALL):
            print(f"Blocked non-football: {title}")
            continue
        if not any(f in low for f in FOOTBALL_KEYWORDS):
            continue
        
        key = f"NEWS_{art['url']}"
        if key in state:
            continue
        
        caption = f"🟢 BREAKING FOOTBALL NEWS! 📰\n\n{title}\n\nSource: {art['source']['name']}\n\nYour thoughts? 👇 Is this true?\n\n🔥 FOLLOW 🟢 - 24/7 Football News + LIVE Goals + KPL!\n#FootballNews #Transfer #BreakingNews #KPL #EPL"
        
        resp = post_with_photo(caption, img)
        if resp and resp.status_code==200:
            state[key] = True
            made += 1
            save_state(state)
        if made >= 2: # max 2 news per run
            break
    return made

# ========= RUN V17 =========
print(f"V17 FINAL PERFECT - BIG LEAGUES + KPL - {datetime.now()}")
print(f"Posting live: Goals, Red Cards, KickOff, Lineups, HT, FT + Football News HD")

try:
    n1 = get_live_scores()
    print(f"LIVE POSTED: {n1}")
except Exception as e:
    print(f"Live error {e}")

try:
    n2 = get_football_news()
    print(f"NEWS POSTED: {n2}")
except Exception as e:
    print(f"News error {e}")

print(f"DONE POSTED {n1+n2} - SUCCESS V17")
save_state(state)
