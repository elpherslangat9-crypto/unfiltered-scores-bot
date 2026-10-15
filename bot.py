import os, requests, json, re, random, time, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

# --- CONFIG ---
PAGE_ID = os.getenv("FB_PAGE_ID")
PAGE_TOKEN = os.getenv("FB_PAGE_TOKEN")
STATE_FILE = "posted_state.json"

LEAGUES = ["eng.1","esp.1","ger.1","ita.1","fra.1","ken.1","usa.1","uefa.champions","uefa.europa","eng.2","mex.1"]
HEADERS = {"User-Agent":"Mozilla/5.0"}

def load_state():
    if os.path.exists(STATE_FILE):
        try: return json.load(open(STATE_FILE))
        except: pass
    return {"kick":{},"last":{},"red":{},"pen":{},"ht":{},"ft":{},"lineup":{},"news":[]}

def save_state(s):
    json.dump(s, open(STATE_FILE,"w"), indent=2)

def fb_text(msg):
    try:
        r=requests.post(f"https://graph.facebook.com/{PAGE_ID}/feed",
            data={"message":msg,"access_token":PAGE_TOKEN}, timeout=15)
        print(f"FB TEXT {r.status_code} {r.text[:200]}")
        return r.status_code==200
    except Exception as e:
        print(f"FB ERR {e}"); return False

def fb_photo(img_url, msg):
    try:
        # download & check size >20kb
        im=requests.get(img_url, headers=HEADERS, timeout=10).content
        if len(im)<20000: return False
        open("tmp.jpg","wb").write(im)
        r=requests.post(f"https://graph.facebook.com/{PAGE_ID}/photos",
            data={"caption":msg,"access_token":PAGE_TOKEN},
            files={"source":open("tmp.jpg","rb")}, timeout=20)
        print(f"FB PHOTO {r.status_code}")
        return r.status_code==200
    except: return False

def get_espn_scoreboard(league):
    try:
        url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard"
        d=requests.get(url, headers=HEADERS, timeout=10).json()
        return d.get("events",[])
    except: return []

def get_summary(event_id):
    try:
        # try all leagues summary - fast method
        url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/summary?event={event_id}"
        return requests.get(url, headers=HEADERS, timeout=8).json()
    except: return {}

def get_goal_info(summary, home_score, away_score):
    """Extract last goal minute and scorer"""
    minute = ""
    scorer = ""
    try:
        # Try scoringPlays
        plays = summary.get("scoringPlays",[]) or summary.get("header",{}).get("competitions",[{}])[0].get("details",[])
        if not plays:
            # Try details in competitions
            comp = summary.get("header",{}).get("competitions",[{}])[0]
            plays = comp.get("details",[]) + comp.get("situation",{}).get("lastPlay",{}).get("text","").split()

        # Find last goal play
        for play in reversed(plays if isinstance(plays, list) else []):
            if isinstance(play, dict):
                # Check if it's a goal
                txt = (play.get("type",{}).get("text","") + " " + play.get("text","")).lower()
                if "goal" in txt or "scoring" in str(play).lower():
                    minute = play.get("clock",{}).get("displayValue","") or play.get("clock","") or ""
                    # minute like 67' or 90'+2
                    if not minute:
                        minute = str(play.get("clock", ""))
                    athletes = play.get("athletesInvolved",[]) or play.get("participants",[])
                    if athletes:
                        scorer = athletes[0].get("athlete",{}).get("displayName","") or athletes[0].get("displayName","")
                    if not scorer:
                        # try to extract from text "Schick (67')"
                        m = re.search(r'([A-Z][a-z]+ [A-Z][a-z]+|[A-Z][a-z]+)\s*\(?\d', play.get("text",""))
                        if m: scorer = m.group(1)
                    if minute or scorer: break

        # Clean minute
        if minute:
            minute = minute.replace("'", "").strip()
            if minute and "'" not in minute: minute = f"{minute}'"
        else:
            # Try to find from summary header clock
            minute = ""
    except Exception as e:
        print(f"goal_info err {e}")
    return minute, scorer

def get_news():
    news_items=[]
    RSS = ["https://www.bbc.com/sport/football/rss.xml","https://www.skysports.com/rss/0,20514,11095,00.xml",
           "https://www.goal.com/en/feeds/news","https://www.espn.com/espn/rss/soccer/news"]
    for rss in RSS:
        try:
            xml=requests.get(rss, headers=HEADERS, timeout=8).text
            root=ET.fromstring(xml)
            for item in root.findall(".//item")[:5]:
                title=item.findtext("title","").strip()
                link=item.findtext("link","").strip()
                # filter football only
                if any(x in title.lower() for x in ["football","premier","laliga","bundesliga","serie a","champions","transfer","arsenal","man","barca","real"]):
                    # get image from enclosure
                    img=""
                    enc=item.find("enclosure")
                    if enc is not None: img=enc.get("url","")
                    if not img:
                        media=item.find("{http://search.yahoo.com/mrss/}content")
                        if media is not None: img=media.get("url","")
                    news_items.append((title,link,img))
        except: continue
    return news_items

# --- MAIN ---
state=load_state()
print("V-ULTIMATE v4 START")

# 1. FETCH ALL GAMES FAST IN PARALLEL
raw=[]
with ThreadPoolExecutor(max_workers=12) as ex:
    for lst in ex.map(get_espn_scoreboard, LEAGUES):
        raw.extend(lst)

print(f"TOTAL LIVE EVENTS {len(raw)}")

posted=0

# 2. PROCESS LIVE GAMES
for ev in raw:
    if posted>=4: break
    try:
        eid=str(ev["id"])
        comp=ev["competitions"][0]
        status=comp["status"]["type"]["name"]
        hs=int(comp["competitors"][0]["score"])
        as_ =int(comp["competitors"][1]["score"])
        home=comp["competitors"][0]["team"]["displayName"]
        away=comp["competitors"][1]["team"]["displayName"]
        league_name=ev.get("league",{}).get("name","Football") if isinstance(ev.get("league"),dict) else comp.get("notes",[{}])[0].get("name","Football")
        cur_score=f"{hs}-{as_}"
        last_score=state["last"].get(eid,"")

        # SUMMARY FOR GOAL DETAIL (only if score changed)
        summary={}
        if cur_score!=last_score and cur_score!="0-0":
            summary=get_summary(eid)

        # --- KICK OFF ---
        if status in ["STATUS_IN_PROGRESS","STATUS_FIRST_HALF","STATUS_SECOND_HALF","STATUS_HALFTIME"] and eid not in state["kick"]:
            msg=f"🟢 KICK-OFF!\n\n{home} vs {away}\n🏆 {league_name}\n\nLive updates here!\n\n🟢 FOLLOW Unfiltered Scores for LIVE Goals!\n🔔 Turn ON Notifications\n\n#UnfilteredScores #LiveScores #FootballLive #FollowForMore #{league_name.replace(' ','')}"
            if fb_text(msg):
                state["kick"][eid]=1; posted+=1; save_state(state)

        # --- GOAL ALERT (ONLY IF SCORE CHANGED AND NOT 0-0 AND GAME IS LIVE) ---
        elif cur_score!=last_score and status in ["STATUS_IN_PROGRESS","STATUS_FIRST_HALF","STATUS_SECOND_HALF"] and last_score!="":
            minute, scorer = get_goal_info(summary, hs, as_)
            minute_str = f" {minute}" if minute else ""
            scorer_str = f"\n⚽ Scorer: {scorer}" if scorer else ""
            msg=f"🟢 GOAL !{minute_str}\n\n{home} {hs} - {as_} {away}{scorer_str}\n🏆 {league_name}\n⏱️ {minute if minute else 'Live'}\n\n🟢 FOLLOW Unfiltered Scores for LIVE Goals!\n\n#UnfilteredScores #LiveScores #{home.replace(' ','')} #{away.replace(' ','')} #GoalAlert"
            if fb_text(msg):
                state["last"][eid]=cur_score; posted+=1; save_state(state)
                continue

        # Update last score tracker
        if cur_score!=last_score:
            state["last"][eid]=cur_score

        # --- HALF TIME ---
        if status=="STATUS_HALFTIME" and eid not in state["ht"]:
            msg=f"🟢 HALF TIME: {home} {hs} - {as_} {away}\n🏆 {league_name}\n\nSecond half soon!\n\n🟢 FOLLOW Unfiltered Scores!\n\n#UnfilteredScores #HalfTime"
            if fb_text(msg):
                state["ht"][eid]=1; posted+=1; save_state(state)

        # --- FULL TIME (NOT as Goal Alert) ---
        if status in ["STATUS_FULL_TIME","STATUS_FINAL"] and eid not in state["ft"]:
            # Only post FT if it finished today (check last score was tracked today)
            if eid in state["last"] or eid in state["kick"]: # means we tracked it live today
                msg=f"🟢 FULL TIME: {home} {hs} - {as_} {away}\n🏆 {league_name}\n⏱️ FT\n\nWhat a game! Your MOTM? 👇\n\n🟢 FOLLOW Unfiltered Scores for LIVE Goals!\n\n#UnfilteredScores #FullTime #{league_name.replace(' ','')}"
                if fb_text(msg):
                    state["ft"][eid]=1; posted+=1; save_state(state)

    except Exception as e:
        print(f"EV ERR {e}"); continue

# 3. NEWS IF NO LIVE POSTS
if posted==0:
    news=get_news()
    for title,link,img in news:
        if posted>=2: break
        if link in state["news"]: continue
        msg=f"🟢 BREAKING: {title}\n\nRead more: {link}\n\n🟢 FOLLOW Unfiltered Scores for Football News!\n🔔 Turn ON Notifications\n\n#UnfilteredScores #FootballNews #BreakingNews #PremierLeague #LaLiga"
        ok=False
        if img: ok=fb_photo(img, msg)
        if not ok: ok=fb_text(msg)
        if ok:
            state["news"].append(link); posted+=1; save_state(state)
            time.sleep(2)

print(f"V-ULTIMATE DONE POSTED {posted}")
save_state(state)
