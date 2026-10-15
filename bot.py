import os, requests, json, re, xml.etree.ElementTree as ET, time
from concurrent.futures import ThreadPoolExecutor

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
        r=requests.post(f"https://graph.facebook.com/v19.0/{PAGE_ID}/feed",
            data={"message":msg,"access_token":PAGE_TOKEN}, timeout=15)
        print(f"FB TEXT {r.status_code} {r.text[:300]}")
        return r.status_code==200
    except Exception as e:
        print(f"FB TEXT ERR {e}"); return False

def fb_photo(img_url, msg):
    try:
        data=requests.get(img_url, headers=HEADERS, timeout=12).content
        if len(data)<20000: return False
        open("tmp.jpg","wb").write(data)
        r=requests.post(f"https://graph.facebook.com/v19.0/{PAGE_ID}/photos",
            data={"caption":msg,"access_token":PAGE_TOKEN},
            files={"source":open("tmp.jpg","rb")}, timeout=20)
        print(f"FB PHOTO {r.status_code}")
        return r.status_code==200
    except Exception as e:
        print(f"PHOTO ERR {e}"); return False

def get_scoreboard(league):
    try:
        url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard"
        j=requests.get(url, headers=HEADERS, timeout=10).json()
        return j.get("events",[])
    except: return []

def get_summary(event_id):
    try:
        url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/summary?event={event_id}"
        return requests.get(url, headers=HEADERS, timeout=8).json()
    except: return {}

def get_goal_info(summary):
    minute=""; scorer=""
    try:
        comp=summary.get("header",{}).get("competitions",[{}])[0]
        details=comp.get("details",[]) or summary.get("scoringPlays",[])
        for play in reversed(details):
            if not isinstance(play, dict): continue
            txt=str(play).lower()
            if "goal" in txt or "scoring" in txt:
                clk=play.get("clock",{})
                if isinstance(clk, dict): minute=clk.get("displayValue","")
                else: minute=str(clk)
                ath=play.get("athletesInvolved",[]) or play.get("participants",[])
                if ath and isinstance(ath, list):
                    first=ath[0]
                    scorer=first.get("athlete",{}).get("displayName","") or first.get("displayName","")
                if not scorer:
                    t=play.get("text","")
                    m=re.search(r'([A-Z][a-z]+\s[A-Z][a-z]+)', t)
                    if m: scorer=m.group(1)
                break
    except: pass
    if minute and "'" not in minute and minute: minute=f"{minute}'"
    return minute, scorer

def get_news():
    items=[]
    RSS=[
        "https://www.bbc.com/sport/football/rss.xml",
        "https://www.skysports.com/rss/0,20514,11095,00.xml",
        "https://www.goal.com/en/feeds/news"
    ]
    for rss in RSS:
        try:
            xml_text=requests.get(rss, headers=HEADERS, timeout=8).text
            root=ET.fromstring(xml_text)
            for it in root.findall(".//item")[:6]:
                title=it.findtext("title","").strip()
                link=it.findtext("link","").strip()
                if not title or not link: continue
                img=""
                enc=it.find("enclosure")
                if enc is not None: img=enc.get("url","")
                if not img:
                    m=it.find("{http://search.yahoo.com/mrss/}content")
                    if m is not None: img=m.get("url","")
                items.append((title,link,img))
        except: continue
    return items

# ========== MAIN ==========
state=load_state()
print("V-ULTIMATE v5 START - ALL FEATURES")

# FAST FETCH ALL LEAGUES IN PARALLEL
raw=[]
with ThreadPoolExecutor(max_workers=12) as ex:
    for lst in ex.map(get_scoreboard, LEAGUES):
        raw.extend(lst)

print(f"TOTAL LIVE EVENTS {len(raw)}")

posted=0

for ev in raw:
    if posted>=4: break
    try:
        if not ev.get("competitions"): continue
        comp=ev["competitions"][0]
        if not comp.get("competitors") or len(comp["competitors"])<2: continue

        eid=str(ev["id"])
        status=comp["status"]["type"]["name"]
        hs=int(comp["competitors"][0]["score"])
        as_=int(comp["competitors"][1]["score"])
        home=comp["competitors"][0]["team"]["displayName"]
        away=comp["competitors"][1]["team"]["displayName"]

        # SAFE league name - FIXES list index error
        league_name="Football"
        try:
            if comp.get("notes") and len(comp["notes"])>0:
                league_name=comp["notes"][0].get("name","Football")
            elif ev.get("league"):
                league_name=ev["league"].get("name","Football")
            if not league_name: league_name="Football"
        except: league_name="Football"

        cur=f"{hs}-{as_}"
        last=state["last"].get(eid,"")

        # GET SUMMARY for lineup / goals / cards
        summary={}
        need_summary = (eid not in state["lineup"]) or (cur!=last and last!="") or (status in ["STATUS_IN_PROGRESS","STATUS_FIRST_HALF","STATUS_SECOND_HALF"])
        if need_summary:
            summary=get_summary(eid)

        # --- 1. LINE-UPS ---
        if eid not in state["lineup"] and status in ["STATUS_IN_PROGRESS","STATUS_FIRST_HALF","STATUS_SECOND_HALF","STATUS_SCHEDULED"]:
            try:
                lineups=[]
                # try to get lineups from summary
                ros=summary.get("rosters",[]) or summary.get("header",{}).get("competitions",[{}])[0].get("competitors",[])
                if summary.get("rosters"):
                    for team in summary.get("rosters",[]):
                        tname=team.get("team",{}).get("displayName","")
                        players=[p.get("athlete",{}).get("displayName","") for p in team.get("roster",[])[:11]]
                        if players: lineups.append(f"{tname}: {', '.join(players[:5])}...")
                if lineups or summary:
                    msg=f"🟢 LINE-UPS: {home} vs {away}\n🏆 {league_name}\n\n" + ("\n".join(lineups) if lineups else "Confirmed line-ups are out! Who will win?") + f"\n\n🟢 FOLLOW Unfiltered Scores!\n\n#UnfilteredScores #LineUp #LiveScores"
                    if len(msg)>100 and fb_text(msg):
                        state["lineup"][eid]=1; posted+=1; save_state(state)
            except: pass

        # --- 2. KICK-OFF ---
        if status in ["STATUS_IN_PROGRESS","STATUS_FIRST_HALF","STATUS_SECOND_HALF"] and eid not in state["kick"]:
            msg=f"🟢 KICK-OFF!\n\n{home} vs {away}\n🏆 {league_name}\n\nLive action started!\n\n🟢 FOLLOW Unfiltered Scores for LIVE Goals!\n🔔 Turn ON Notifications\n\n#UnfilteredScores #LiveScores #KICKOFF"
            if fb_text(msg):
                state["kick"][eid]=1; posted+=1; save_state(state); state["last"][eid]=cur; continue

        # --- 3. GOAL ALERT WITH MINUTE + SCORER ---
        if cur!=last and last!="" and status in ["STATUS_IN_PROGRESS","STATUS_FIRST_HALF","STATUS_SECOND_HALF"]:
            minute, scorer = get_goal_info(summary)
            minute_str = f" {minute}" if minute else ""
            scorer_str = f"\n⚽ Scorer: {scorer}" if scorer else ""
            msg=f"🟢 GOAL !{minute_str}\n\n{home} {hs} - {as_} {away}{scorer_str}\n🏆 {league_name}\n⏱️ {minute if minute else 'Live'}\n\n🟢 FOLLOW Unfiltered Scores for LIVE Goals!\n\n#UnfilteredScores #GoalAlert #{home.replace(' ','')} #{away.replace(' ','')}"
            if fb_text(msg):
                state["last"][eid]=cur; posted+=1; save_state(state); continue

        if cur!=last: state["last"][eid]=cur

        # --- 4. RED CARD (from commentary) ---
        if eid not in state["red"]:
            try:
                txt=str(summary).lower()
                if "red card" in txt:
                    msg=f"🟢 RED CARD! 🔴\n\n{home} vs {away}\n🏆 {league_name}\n\nSomeone sent off!\n\n🟢 FOLLOW Unfiltered Scores!\n\n#RedCard #UnfilteredScores"
                    if fb_text(msg): state["red"][eid]=1; posted+=1; save_state(state)
            except: pass

        # --- 5. PENALTY ---
        if eid not in state["pen"]:
            try:
                txt=str(summary).lower()
                if "penalty" in txt and "penalty awarded" in txt:
                    msg=f"🟢 PENALTY! 🎯\n\n{home} vs {away}\n🏆 {league_name}\n\nPenalty awarded!\n\n🟢 FOLLOW Unfiltered Scores!\n\n#Penalty #UnfilteredScores"
                    if fb_text(msg): state["pen"][eid]=1; posted+=1; save_state(state)
            except: pass

        # --- 6. HALF TIME ---
        if status=="STATUS_HALFTIME" and eid not in state["ht"]:
            msg=f"🟢 HALF TIME: {home} {hs} - {as_} {away}\n🏆 {league_name}\n\nSecond half coming!\n\n🟢 FOLLOW Unfiltered Scores!\n\n#HalfTime #UnfilteredScores"
            if fb_text(msg): state["ht"][eid]=1; posted+=1; save_state(state)

        # --- 7. FULL TIME ---
        if status in ["STATUS_FULL_TIME","STATUS_FINAL","STATUS_FINAL_PEN"] and eid not in state["ft"]:
            if eid in state["kick"] or eid in state["last"]: # only if tracked today
                msg=f"🟢 FULL TIME: {home} {hs} - {as_} {away}\n🏆 {league_name}\n⏱️ FT\n\nYour MOTM? 👇\n\n🟢 FOLLOW Unfiltered Scores for LIVE Goals!\n\n#FullTime #UnfilteredScores #{league_name.replace(' ','')}"
                if fb_text(msg): state["ft"][eid]=1; posted+=1; save_state(state)

    except Exception as e:
        print(f"EV ERR {e}")
        continue

# --- 8. NEWS WITH PHOTO WHEN NO LIVE ---
if posted==0:
    news=get_news()
    for title,link,img in news:
        if posted>=2: break
        if link in state["news"]: continue
        msg=f"🟢 BREAKING: {title}\n\nRead more: {link}\n\n🟢 FOLLOW Unfiltered Scores for Breaking News!\n🔔 Turn ON Notifications\n\n#UnfilteredScores #FootballNews #BreakingNews"
        ok=False
        if img: ok=fb_photo(img, msg)
        if not ok: ok=fb_text(msg)
        if ok:
            state["news"].append(link); posted+=1; save_state(state); time.sleep(2)

print(f"V-ULTIMATE DONE POSTED {posted}")
save_state(state)
