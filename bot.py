import os, json, requests, feedparser, re
from datetime import datetime
PAGE_ID = "1293090263895541"
TOKEN = os.getenv("FB_TOKEN")
STATE_FILE = "posted_state.json"
print(f"=== V20.5 FINAL FORCE PAGE_ID={PAGE_ID} ===")
NON_FOOTBALL = ["usyk","boxing","mcilroy","golf","tennis","f1","nba","rugby","cricket","ufc"]
LEAGUES = ["eng.1","esp.1","ger.1","ita.1","fra.1","ned.1","por.1","sco.1","bel.1","tur.1","eng.2","usa.1","bra.1","sau.1","uefa.champions","uefa.europa","uefa.europa.conf","caf.champions"]
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE,'r') as f: return json.load(f)
        except: return {}
    return {}
def save_state(s):
    with open(STATE_FILE,'w') as f: json.dump(s,f)
state = load_state()
def get_hd_image_from_article(article_url):
    try:
        headers = {"User-Agent":"Mozilla/5.0"}
        html = requests.get(article_url, timeout=10, headers=headers).text
        og_match = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html, re.I)
        if og_match:
            img = og_match.group(1)
            img = img.replace("320x180","1024x576").replace("240x135","1024x576").replace("624x351","1024x576")
            if "logo" not in img.lower(): return img
    except: pass
    return None
def post_with_photo(caption, image_url):
    try:
        r = requests.get(image_url, timeout=15, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code != 200 or len(r.content) < 15000: return False
        with open("temp.jpg","wb") as f: f.write(r.content)
        with open("temp.jpg","rb") as img_file:
            url = f"https://graph.facebook.com/{PAGE_ID}/photos"
            resp = requests.post(url, data={"caption":caption,"access_token":TOKEN}, files={"source":img_file}, timeout=25)
        print(f"FB PHOTO {resp.status_code} {resp.text[:500]}")
        return resp.status_code == 200
    except Exception as e:
        print(f"Photo error {e}")
        return False
def post_text(text):
    try:
        url = f"https://graph.facebook.com/{PAGE_ID}/feed"
        resp = requests.post(url, data={"message":text,"access_token":TOKEN}, timeout=15)
        print(f"FB TEXT {resp.status_code}")
        return resp.status_code == 200
    except: return False
live_posted = 0
for league_code in LEAGUES:
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/scoreboard"
        data = requests.get(url, timeout=10).json()
        for ev in data.get("events", []):
            try:
                comp = ev["competitions"][0]
                status_state = ev["status"]["type"]["state"]
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
                league_name = data["leagues"][0]["name"] if data.get("leagues") else league_code
                league_logo = data["leagues"][0]["logos"][0]["href"] if data.get("leagues") and data["leagues"][0].get("logos") else home_logo
                ev_id = ev["id"]
                score_str = f"{home_name} {home_score}-{away_score} {away_name}"
                minute_str = display_clock or short_detail
                lineup_key = f"{ev_id}_LINEUP"
                if status_state == "pre" and lineup_key not in state:
                    cap = f"📋 LINEUPS ARE OUT!\n\n{home_name} vs {away_name}\n🏆 {league_name}\n⏰ {short_detail}\n\nPredict! 👇\nFOLLOW for LIVE GOALS!"
                    if post_with_photo(cap, league_logo):
                        state[lineup_key]=True; live_posted+=1; save_state(state)
                k_key = f"{ev_id}_KICK"
                if status_state == "in" and k_key not in state:
                    cap = f"🟢 KICK-OFF! LIVE NOW\n\n{home_name} vs {away_name}\n🏆 {league_name}\n⏱️ {minute_str}\n\nWho scores first? 👇"
                    if post_with_photo(cap, league_logo):
                        state[k_key]=True; live_posted+=1; save_state(state)
                g_key = f"{ev_id}_GOAL_{home_score}_{away_score}"
                if status_state == "in" and g_key not in state and not (home_score=="0" and away_score=="0"):
                    cap = f"⚽ GOAL! {minute_str}\n\n{score_str}\n🏆 {league_name}\n⏱️ {minute_str}\n\nGame over? 👇"
                    if post_with_photo(cap, league_logo):
                        state[g_key]=True; live_posted+=1; save_state(state)
                for det in comp.get("details",[]):
                    if "red card" in (det.get("text","")+det.get("type",{}).get("text","")).lower():
                        r_key = f"{ev_id}_RED_{det.get('id','')}"
                        if r_key not in state:
                            cap = f"🟥 RED CARD! {minute_str}\n\n{score_str}\n🏆 {league_name}\n⚠️ {det.get('text','')}\n\nGame changed! 👇"
                            if post_with_photo(cap, league_logo):
                                state[r_key]=True; live_posted+=1; save_state(state)
                ht_key = f"{ev_id}_HT"
                if "HALFTIME" in status_name.upper() and ht_key not in state:
                    cap = f"⏸️ HALF TIME\n\n{score_str}\n🏆 {league_name}\n\nThoughts? 👇"
                    if post_text(cap):
                        state[ht_key]=True; live_posted+=1; save_state(state)
                ft_key = f"{ev_id}_FT"
                if status_state == "post" and ft_key not in state:
                    cap = f"✅ FULL TIME\n\n{score_str}\n🏆 {league_name}\n\nRate 1-10! 👇"
                    if post_with_photo(cap, league_logo):
                        state[ft_key]=True; live_posted+=1; save_state(state)
            except: continue
    except: continue
print(f"LIVE POSTED: {live_posted}")
news_posted = 0
try:
    feeds = ["http://feeds.bbci.co.uk/sport/football/rss.xml","https://www.espn.com/espn/rss/soccer/news"]
    for feed_url in feeds:
        if news_posted >= 2: break
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:10]:
            if news_posted >= 2: break
            if any(x in entry.title.lower() for x in NON_FOOTBALL): continue
            n_key = f"NEWS_{entry.link}"
            if n_key in state: continue
            img_url = None
            if hasattr(entry,'media_thumbnail') and entry.media_thumbnail:
                img_url = entry.media_thumbnail[0]['url'].replace("240x135","1024x576")
            hd_img = get_hd_image_from_article(entry.link)
            if hd_img: img_url = hd_img
            if not img_url: continue
            if "logo" in img_url.lower(): continue
            cap = f"🟢 BREAKING FOOTBALL NEWS! 📰\n\n{entry.title}\n\nSource: BBC Sport\n\nYour thoughts? 👇\n🔥 FOLLOW - 24/7 Football + LIVE Goals!\n#FootballNews"
            if post_with_photo(cap, img_url):
                state[n_key]=True; news_posted+=1; save_state(state)
except Exception as e:
    print(f"News error {e}")
print(f"NEWS POSTED: {news_posted}")
print(f"DONE POSTED {live_posted+news_posted} - V20.5 FINAL")
save_state(state)
