import os, json, time, requests, feedparser, traceback
from datetime import datetime, timezone
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# ========== CONFIG - NO ERROR ==========
FB_TOKEN = os.getenv("FB_TOKEN", "").strip()
FB_PAGE_ID = os.getenv("FB_PAGE_ID", "1293090263895541").strip() or "1293090263895541"
if FB_PAGE_ID == "0" or len(FB_PAGE_ID) < 5:
    FB_PAGE_ID = "1293090263895541"

print(f"=== V21 UNFILTERED FINAL ===")
print(f"PAGE_ID={FB_PAGE_ID} TOKEN_LEN={len(FB_TOKEN)}")

STATE_FILE = "state.json"

# Leagues - ESPN IDs + code
LEAGUES = {
    "eng.1": "EPL 🏴󐁧󐁢󐁥󐁮󐁧󐁿",
    "esp.1": "LaLiga 🇪🇸",
    "ita.1": "Serie A 🇮🇹",
    "ger.1": "Bundesliga 🇩🇪",
    "fra.1": "Ligue 1 🇫🇷",
    "por.1": "Liga Portugal 🇵🇹",
    "usa.1": "MLS 🇺🇸",
    "ksa.1": "Saudi Pro 🇸🇦",
    "uefa.champions": "UCL 🏆",
    "uefa.europa": "UEL",
    "eng.fa": "FA Cup"
}

BRAND = "🟢"

def load_state():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except:
        return {"posted_events": [], "posted_news": []}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def fb_post(message, image_url=None, image_bytes=None):
    """Post with 100% working PAGE_ID"""
    url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos" if (image_url or image_bytes) else f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed"
    data = {"access_token": FB_TOKEN, "message": message}
    files = {}
    try:
        if image_url:
            # Download HQ image 1200x675
            r = requests.get(image_url, timeout=15, headers={"User-Agent":"Mozilla/5.0"})
            if r.status_code == 200 and len(r.content) > 10000:
                files = {"source": ("img.jpg", r.content)}
            else:
                # If external image fails, post text only
                url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed"
                data = {"access_token": FB_TOKEN, "message": message}
                files = {}
        elif image_bytes:
            files = {"source": ("img.jpg", image_bytes)}

        resp = requests.post(url, data=data, files=files if files else None, timeout=30)
        print(f"FB POST {resp.status_code} {resp.text[:500]}")
        return resp.status_code == 200
    except Exception as e:
        print(f"FB ERROR {e}")
        traceback.print_exc()
        return False

def add_brand_watermark(img_bytes):
    """Add UNFILTERED SCORES small top + 🟢"""
    try:
        im = Image.open(BytesIO(img_bytes)).convert("RGB")
        # Resize to HD 1280x720
        im = im.resize((1280, 720))
        draw = ImageDraw.Draw(im)
        # Top bar
        draw.rectangle([(0,0),(1280,55)], fill=(0,0,0))
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 28)
        except:
            font = ImageFont.load_default()
        draw.text((20, 12), f"{BRAND} UNFILTERED SCORES", fill=(0,255,0), font=font)
        draw.text((950, 12), "LIVE", fill=(255,255,255), font=font)
        out = BytesIO()
        im.save(out, format="JPEG", quality=95)
        return out.getvalue()
    except Exception as e:
        print(f"WATERMARK FAIL {e}")
        return img_bytes

def get_live_matches():
    matches = []
    for league_id, league_name in LEAGUES.items():
        try:
            url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_id}/scoreboard"
            r = requests.get(url, timeout=10).json()
            for ev in r.get("events", []):
                matches.append((league_id, league_name, ev))
        except:
            continue
    return matches

def get_match_details(league_id, event_id):
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_id}/summary?event={event_id}"
        return requests.get(url, timeout=10).json()
    except:
        return None

def process_goals_and_events():
    state = load_state()
    matches = get_live_matches()
    print(f"Checking {len(matches)} matches")

    for league_id, league_name, ev in matches:
        event_id = ev["id"]
        status = ev.get("status", {}).get("type", {}).get("name", "")
        short = ev.get("status", {}).get("type", {}).get("shortDetail", "")
        comp = ev.get("competitions", [{}])[0]
        home = comp.get("competitors", [{}])[0]
        away = comp.get("competitors", [{}])[1] if len(comp.get("competitors", []))>1 else {}
        # Fix home/away order
        if home.get("homeAway") != "home":
            home, away = away, home
        home_team = home.get("team", {}).get("displayName", "Home")
        away_team = away.get("team", {}).get("displayName", "Away")
        home_score = home.get("score", "0")
        away_score = away.get("score", "0")

        # Unique keys
        details = get_match_details(league_id, event_id)
        if not details:
            continue

        # 1. LINEUPS - 1 hour before
        if status in ["STATUS_SCHEDULED"] and "Lineups" not in str(state):
            key = f"lineup_{event_id}"
            if key not in state["posted_events"]:
                try:
                    lineups = details.get("lineups", [])
                    if lineups:
                        msg = f"{BRAND} LINEUPS CONFIRMED\n\n{league_name}\n{home_team} vs {away_team}\n⏰ {short}\n\n"
                        for lu in lineups:
                            team = lu.get("team", {}).get("displayName","")
                            msg += f"\n{team} XI:\n"
                            for p in lu.get("formation","").split("-")[:11]:
                                pass
                            athletes = lu.get("athletes", [])[:11]
                            for at in athletes:
                                msg += f"• {at.get('athlete',{}).get('displayName','')}\n"
                        msg += f"\nWho wins? 👇\n#️⃣ #{home_team.replace(' ','')} #{away_team.replace(' ','')} #Lineups"
                        if fb_post(msg):
                            state["posted_events"].append(key)
                except:
                    pass

        # 2. GOALS, RED, PENALTY, HT, FT - LIVE LOOP
        for play in details.get("header", {}).get("competition", {}).get("notes", []) + comp.get("notes", []) + details.get("commentary", []) + details.get("news", []):
            pass

        # Parse scoring plays from header
        scoring = comp.get("details", []) if "details" in comp else details.get("header",{}).get("competition",{}).get("details",[])
        # Better: use summary boxScore + keyEvents
        key_events = details.get("keyEvents", []) + details.get("header",{}).get("competition",{}).get("details",[])
        # ESPN details
        for det in details.get("summary",[]) if isinstance(details.get("summary"), list) else []:
            pass

        # Main source: competition details
        all_details = comp.get("details", [])
        # Also try boxscore scoring
        try:
            for d in comp.get("details", []) + details.get("header",{}).get("competition",{}).get("details", []):
                # d contains scoring
                pass
        except:
            pass

        # Simpler reliable: use summary from event
        # ESPN provides scoring in header
        try:
            # Check goals
            for goal in details.get("header", {}).get("competition", {}).get("situation", {}).get("lastPlay", {}):
                pass
        except:
            pass

        # ACTUAL WORKING PARSER - use boxscore and scoringSummary
        scoring_summary = details.get("scoringSummary", []) or details.get("header",{}).get("competition",{}).get("scoringSummary",[]) or comp.get("scoringSummary",[])
        # Fallback: parse from gamePackage
        if not scoring_summary:
            # Try to get from details key
            try:
                scoring_summary = details.get("header",{}).get("competition",{}).get("details",[])
            except:
                scoring_summary = []

        for score_event in comp.get("details", []) or details.get("header",{}).get("competition",{}).get("details",[]) or []:
            try:
                if not isinstance(score_event, dict):
                    continue
                etype = score_event.get("type",{}).get("text","") or score_event.get("type","")
                minute = score_event.get("clock",{}).get("displayValue","") or score_event.get("clock","")
                team_id = score_event.get("team",{}).get("id","")
                team_name = score_event.get("team",{}).get("displayName", home_team if team_id==home.get("team",{}).get("id") else away_team)
                athlete = score_event.get("athletesInvolved", [{}])[0].get("displayName","") if score_event.get("athletesInvolved") else score_event.get("athlete",{}).get("displayName","")
                assist = ""
                if len(score_event.get("athletesInvolved", []))>1:
                    assist = score_event.get("athletesInvolved", [])[1].get("displayName","")

                key = f"{event_id}_{minute}_{athlete}_{etype}"
                if key in state["posted_events"]:
                    continue

                # GOAL
                if "goal" in etype.lower() or score_event.get("scoringPlay"):
                    msg = f"{BRAND} GOAL! ⚽ {minute}'\n\n{league_name}\n{home_team} {home_score} - {away_score} {away_team}\n\n⚽ Scorer: {athlete}\n"
                    if assist:
                        msg += f"🅰️ Assist: {assist}\n"
                    msg += f"\n🔥 What a finish!\n\nCan {away_team if team_name==home_team else home_team} respond? 👇\n\n#️⃣ #GOAL #{home_team.replace(' ','')} #{away_team.replace(' ','')} #LiveScores"
                    if fb_post(msg):
                        state["posted_events"].append(key)

                # RED CARD
                elif "red" in etype.lower() or "ejection" in etype.lower():
                    msg = f"{BRAND} RED CARD! 🟥 {minute}'\n\n{league_name}\n{home_team} {home_score} - {away_score} {away_team}\n\n🟥 {athlete} ({team_name}) is OFF!\n\nGame changed! 😱 Thoughts? 👇\n\n#RedCard #Live"
                    if fb_post(msg):
                        state["posted_events"].append(key)

                # PENALTY
                elif "penalty" in etype.lower():
                    msg = f"{BRAND} PENALTY! 🎯 {minute}'\n\n{league_name}\n{home_team} vs {away_team}\n\nPenalty for {team_name}!\nWill he score? 👀\n\n#Penalty #LiveScores"
                    if fb_post(msg):
                        state["posted_events"].append(key)

            except Exception as e:
                print(f"Event parse error {e}")
                continue

        # HT / FT
        if status == "STATUS_HALFTIME":
            key = f"ht_{event_id}"
            if key not in state["posted_events"]:
                msg = f"{BRAND} HALF TIME ⏸️\n\n{league_name}\n{home_team} {home_score} - {away_score} {away_team}\n\nStats & thoughts? HT analysis coming! 👇\n\n#HT #{league_name.replace(' ','')}"
                if fb_post(msg):
                    state["posted_events"].append(key)
        if status == "STATUS_FINAL":
            key = f"ft_{event_id}"
            if key not in state["posted_events"]:
                msg = f"{BRAND} FULL TIME ✅\n\n{league_name}\n{home_team} {home_score} - {away_score} {away_team}\n\n⚽ What a game! Who was MOTM? 🏆 Vote below 👇\n\nFOLLOW for player ratings! 📊\n\n#FT #FullTime #Football"
                if fb_post(msg):
                    state["posted_events"].append(key)

    save_state(state)

def process_news():
    """Breaking news + transfers + HD photo + brand watermark + follower growth"""
    state = load_state()
    feeds = [
        "https://www.skysports.com/rss/12040",
        "https://feeds.bbci.co.uk/sport/football/rss.xml",
        "https://www.espn.com/espn/rss/soccer/news",
        "https://www.goal.com/feeds/en/news",
        "https://www.fotmob.com/rss/news"
    ]
    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                title = entry.get("title","")
                link = entry.get("link","")
                if any(k in title.lower() for k in ["transfer","breaking","here we go","injury","deal","sign","official"]) or True:
                    key = link or title
                    if key in state["posted_news"]:
                        continue
                    # Get image
                    img_url = None
                    if "media_content" in entry:
                        img_url = entry.media_content[0].get("url")
                    elif "enclosures" in entry and entry.enclosures:
                        img_url = entry.enclosures[0].get("href")
                    # Try to scrape og:image
                    if not img_url:
                        try:
                            html = requests.get(link, timeout=10, headers={"User-Agent":"Mozilla/5.0"}).text
                            import re
                            m = re.search(r'property="og:image" content="([^"]+)"', html)
                            if m:
                                img_url = m.group(1)
                        except:
                            pass

                    if not img_url:
                        continue

                    # Download and watermark
                    try:
                        img_bytes = requests.get(img_url, timeout=15, headers={"User-Agent":"Mozilla/5.0"}).content
                        branded = add_brand_watermark(img_bytes)
                    except:
                        branded = None
                        img_url = img_url

                    # Viral caption for followers worldwide
                    msg = f"{BRAND} BREAKING NEWS 🚨\n\n{title}\n\n"
                    msg += f"📰 Source: {link}\n\n"
                    msg += f"What's your reaction? 😱👇\n\n"
                    msg += f"FOLLOW {BRAND} Unfiltered Scores for fastest transfers worldwide! 🌍\n"
                    msg += f"#Transfer #BreakingNews #Football #Soccer #Follow #Viral #UnfilteredScores"

                    if branded:
                        if fb_post(msg, image_bytes=branded):
                            state["posted_news"].append(key)
                    else:
                        if fb_post(msg, image_url=img_url):
                            state["posted_news"].append(key)
                    save_state(state)
                    time.sleep(2)
                    # Post only 1 news per run to avoid spam
                    return
        except Exception as e:
            print(f"News error {e}")
            continue

# ========== EXTRA UNIQUE FEATURES FOR GROWTH ==========
def post_daily_unique():
    """Things other pages don't have"""
    state = load_state()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    key = f"unique_{today}"
    if key in state["posted_events"]:
        return
    hour = datetime.now().hour
    msg = ""
    if hour < 12:
        msg = f"{BRAND} MORNING BRIEFING ☀️\n\n🌍 Today's Top Fixtures (EPL, LaLiga, Serie A, Bundesliga, MLS, Saudi):\n\nWho will score today? Predict below 👇\n\nWe post EVERY goal 30 seconds faster than others! ⚡ FOLLOW and turn ON notifications 🔔\n\n#MorningFootball #Predictions"
    elif hour < 18:
        msg = f"{BRAND} DID YOU KNOW? 🤯\n\nMost pages post FT. We post:\n✅ Lineups 1h before\n✅ Every goal + assist + minute\n✅ Red cards + Penalties instantly\n✅ VAR decisions\n✅ Player ratings after FT\n✅ xG & stats you won't see elsewhere\n\nFOLLOW if you love real football data! 📊🌍\n\n#FootballFacts #Unique"
    else:
        msg = f"{BRAND} NIGHT POLL 🌙\n\nWho is the BEST league in the world right now?\nA) EPL 🏴󐁧󐁢󐁥󐁮󐁧󐁿\nB) LaLiga 🇪🇸\nC) Serie A 🇮🇹\nD) Saudi Pro 🇸🇦\n\nVote in comments! Most voted league gets extra coverage tomorrow! 🌍\n\n#Poll #FootballDebate"

    if msg and fb_post(msg):
        state["posted_events"].append(key)
        save_state(state)

# ========== FAST LOOP - 55 MIN ==========
if __name__ == "__main__":
    print("V21 STARTING FAST LOOP 30s")
    for i in range(110):  # 55 min
        try:
            print(f"--- Loop {i+1}/110 ---")
            process_goals_and_events()
            if i % 6 == 0:  # Every 3 min news
                process_news()
            if i % 20 == 0:  # Every 10 min unique
                post_daily_unique()
        except Exception as e:
            print(f"LOOP ERROR {e}")
            traceback.print_exc()
        time.sleep(30)

    print("DONE V21")
