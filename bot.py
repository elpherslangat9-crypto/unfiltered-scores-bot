import os, requests, json, re, xml.etree.ElementTree as ET, time, random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

PAGE_ID = os.getenv("FB_PAGE_ID")
PAGE_TOKEN = os.getenv("FB_PAGE_TOKEN")
STATE_FILE = "posted_state.json"

LEAGUES = ["eng.1","esp.1","ger.1","ita.1","fra.1","ken.1","usa.1","uefa.champions","uefa.europa","eng.2","mex.1"]
HEADERS = {"User-Agent":"Mozilla/5.0"}

# Viral hashtags for growth
VIRAL_TAGS = "#UnfilteredScores #LiveScores #FootballLive #GoalAlert #PremierLeague #LaLiga #Bundesliga #SerieA #ChampionsLeague #FollowForMore #ViralFootball #FootballNews"

def load_state():
    if os.path.exists(STATE_FILE):
        try: return json.load(open(STATE_FILE))
        except: pass
    return {"kick":{},"last":{},"red":{},"pen":{},"ht":{},"ft":{},"lineup":{},"news":[],"var":{}}

def save_state(s):
    json.dump(s, open(STATE_FILE,"w"), indent=2)

def fb_text(msg):
    try:
        r=requests.post(f"https://graph.facebook.com/v19.0/{PAGE_ID}/feed",
            data={"message":msg,"access_token":PAGE_TOKEN}, timeout=20)
        print(f"FB TEXT {r.status_code} {r.text[:400]}")
        return r.status_code==200
    except Exception as e:
        print(f"FB TEXT ERR {e}"); return False

# FIXED PHOTO FUNCTION - WAS GIVING 400 ERROR
def fb_photo(img_url, msg):
    try:
        data=requests.get(img_url, headers=HEADERS, timeout=15).content
        print(f"IMG SIZE {len(data)}")
        if len(data)<15000: return False
        open("tmp.jpg","wb").write(data)
        r=requests.post(f"https://graph.facebook.com/v19.0/{PAGE_ID}/photos",
            data={"caption":msg,"access_token":PAGE_TOKEN, "published":"true"},
            files={"source":open("tmp.jpg","rb")}, timeout=25)
        print(f"FB PHOTO {r.status_code} {r.text[:400]}")
        return r.status_code==200
    except Exception as e:
        print(f"PHOTO ERR {e}"); return False

def get_scoreboard(league):
    try:
        url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard"
        j=requests.get(url, headers=HEADERS, timeout=12).json()
        return j.get("events",[])
    except Exception as e:
        print(f"SCOREBOARD {league} ERR {e}"); return []

def get_summary(event_id):
    try:
        url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/summary?event={event_id}"
        return requests.get(url, headers=HEADERS, timeout=10).json()
    except: return {}

def get_goal_info(summary):
    minute=""; scorer=""; team=""
    try:
        comp=summary.get("header",{}).get("competitions",[{}])[0]
        details=comp.get("details",[]) or summary.get("scoringPlays",[]) or []
        for play in reversed(details):
            if not isinstance(play, dict): continue
            txt=str(play).lower()
            if "goal" in txt or "scoringplay" in txt or "scoring" in txt:
                clk=play.get("clock",{})
                if isinstance(clk, dict): minute=clk.get("displayValue","")
                else: minute=str(clk)
                ath=play.get("athletesInvolved",[]) or play.get("participants",[])
                if ath:
                    first=ath[0]
                    scorer=first.get("athlete",{}).get("displayName","") or first.get("displayName","")
                    team=first.get("team",{}).get("displayName","") if isinstance(first.get("team"), dict) else ""
                if not scorer and play.get("text"):
                    m=re.search(r'([A-Z][a-z]+ [A-Z][a-z]+)', play.get("text",""))
                    if m: scorer=m.group(1)
                break
    except: pass
    if minute and "'" not in minute and minute: minute=f"{minute}'"
    return minute, scorer, team

def get_news():
    items=[]
    RSS=[
        "https://www.bbc.com/sport/football/rss.xml",
        "https://www.skysports.com/rss/0,20514,11095,00.xml",
        "https://www.goal.com/en/feeds/news",
        "https://feeds.bbci.co.uk/sport/football/rss.xml"
    ]
    for rss in RSS:
        try:
            xml_text=requests.get(rss, headers=HEADERS, timeout=10).text
            root=ET.fromstring(xml_text)
            for it in root.findall(".//item")[:8]:
                title=it.findtext("title","").strip()
                link=it.findtext("link","").strip()
                if not title or not link: continue
                img=""
                enc=it.find("enclosure")
                if enc is not None: img=enc.get("url","")
                if not img:
                    m=it.find("{http://search.yahoo.com/mrss/}content")
                    if m is not None: img=m.get("url","")
                if not img:
                    m2=it.find("{http://search.yahoo.com/mrss/}thumbnail")
                    if m2 is not None: img=m2.get("url","")
                items.append((title,link,img))
        except: continue
    return items

# ========== MAIN PERFECT BOT ==========
state=load_state()
print(f"V-ULTIMATE v6 PERFECT START {datetime.now()} - PAGE_ID {PAGE_ID}")

raw=[]
with ThreadPoolExecutor(max_workers=12) as ex:
    for lst in ex.map(get_scoreboard, LEAGUES):
        raw.extend(lst)

print(f"TOTAL EVENTS {len(raw)}")
random.shuffle(raw) # mix leagues for variety

posted=0

for ev in raw:
    if posted>=4: break
    try:
        if not ev.get("competitions"): continue
        comp=ev["competitions"][0]
        if not comp.get("competitors") or len(comp["competitors"])<2: continue

        eid=str(ev["id"])
        status=comp["status"]["type"]["name"]
        status_display=comp["status"]["type"].get("detail","Live")
        hs=int(comp["competitors"][0]["score"])
        as_=int(comp["competitors"][1]["score"])
        home=comp["competitors"][0]["team"]["displayName"]
        away=comp["competitors"][1]["team"]["displayName"]
        home_short=comp["competitors"][0]["team"].get("abbreviation", home)
        away_short=comp["competitors"][1]["team"].get("abbreviation", away)

        league_name="Football"
        try:
            if comp.get("notes") and len(comp["notes"])>0 and comp["notes"][0].get("name"):
                league_name=comp["notes"][0].get("name")
            elif ev.get("league") and ev["league"].get("name"):
                league_name=ev["league"].get("name")
        except: league_name="Football"

        cur=f"{hs}-{as_}"
        last=state["last"].get(eid,"")

        summary={}
        if eid not in state["lineup"] or cur!=last or status in ["STATUS_IN_PROGRESS","STATUS_FIRST_HALF","STATUS_SECOND_HALF","STATUS_HALFTIME"]:
            summary=get_summary(eid)

        # --- 1. LINE-UPS (BIG FOR ENGAGEMENT) ---
        if eid not in state["lineup"] and status in ["STATUS_SCHEDULED","STATUS_IN_PROGRESS","STATUS_FIRST_HALF"]:
            try:
                lineup_text=""
                if summary.get("rosters"):
                    for team_roster in summary["rosters"][:2]:
                        tname=team_roster.get("team",{}).get("displayName","")
                        starters=[p.get("athlete",{}).get("displayName","") for p in team_roster.get("roster",[])[:11] if p.get("athlete")]
                        if starters:
                            lineup_text+=f"🔹 {tname}: {', '.join(starters[:4])}...\n"
                msg=f"🟢 LINE-UPS ARE IN!\n\n{home} vs {away}\n🏆 {league_name}\n⏰ {status_display}\n\n{lineup_text if lineup_text else 'Confirmed starting XI are out!'}\n\nWho will WIN this one? Predict score! 👇\n\n🟢 FOLLOW Unfiltered Scores for LIVE updates!\n🔔 Turn ON Notifications\n\n{VIRAL_TAGS}"
                if fb_text(msg):
                    state["lineup"][eid]=1; posted+=1; save_state(state); continue
            except Exception as e:
                print(f"LINEUP ERR {e}")

        # --- 2. KICK-OFF ---
        if status in ["STATUS_IN_PROGRESS","STATUS_FIRST_HALF","STATUS_SECOND_HALF"] and eid not in state["kick"]:
            msg=f"🟢 KICK-OFF! 🔥\n\n{home} vs {away}\n🏆 {league_name}\n⏱️ LIVE\n\nThe match is ON! Who scores first?\n\n🟢 FOLLOW Unfiltered Scores for every GOAL LIVE!\n🔔 Turn ON Notifications - Don't miss a goal!\n\n#LiveScores #{home_short}vs{away_short} #{league_name.replace(' ','')} {VIRAL_TAGS}"
            if fb_text(msg):
                state["kick"][eid]=1; state["last"][eid]=cur; posted+=1; save_state(state); continue

        # --- 3. GOAL ALERT WITH MINUTE + SCORER (YOUR REQUEST) ---
        if cur!=last and last!="" and status in ["STATUS_IN_PROGRESS","STATUS_FIRST_HALF","STATUS_SECOND_HALF","STATUS_IN_PROGRESS","STATUS_SECOND_HALF"]:
            minute, scorer, team_goal = get_goal_info(summary)
            minute_str = f" {minute}" if minute else ""
            scorer_str = f"\n⚽ Scorer: {scorer}" if scorer else ""
            team_emoji = "⚽"
            if team_goal and home in team_goal: team_emoji = f"⚽ {home}"
            elif team_goal and away in team_goal: team_emoji = f"⚽ {away}"

            msg=f"🟢 GOAL ALERT!{minute_str} 🔥{team_emoji}\n\n{home} {hs} - {as_} {away}{scorer_str}\n🏆 {league_name}\n⏱️ {minute if minute else 'Live'} | {status_display}\n\nIs this the winner? Comment! 👇\n\n🟢 FOLLOW Unfiltered Scores - FASTEST Goal Alerts!\n🔔 Turn ON Notifications\n\n#GOAL #{home_short} #{away_short} #GoalAlert {VIRAL_TAGS}"
            if fb_text(msg):
                state["last"][eid]=cur; posted+=1; save_state(state); continue

        if cur!=last: state["last"][eid]=cur

        # --- 4. RED CARD ---
        if eid not in state["red"]:
            try:
                if "red card" in str(summary).lower() or "ejected" in str(summary).lower():
                    msg=f"🟢 RED CARD! 🔴😱\n\n{home} vs {away}\n🏆 {league_name}\n\nDRAMA! Player sent OFF!\n\nCan they hold on? 👇\n\n🟢 FOLLOW Unfiltered Scores for LIVE Drama!\n\n#RedCard #{home_short}vs{away_short} {VIRAL_TAGS}"
                    if fb_text(msg): state["red"][eid]=1; posted+=1; save_state(state); continue
            except: pass

        # --- 5. PENALTY ---
        if eid not in state["pen"]:
            try:
                if "penalty" in str(summary).lower() and "awarded" in str(summary).lower():
                    msg=f"🟢 PENALTY AWARDED! 🎯\n\n{home} vs {away}\n🏆 {league_name}\n\nWill they SCORE? 🤔\n\n🟢 FOLLOW Unfiltered Scores!\n\n#Penalty #{home_short}vs{away_short} {VIRAL_TAGS}"
                    if fb_text(msg): state["pen"][eid]=1; posted+=1; save_state(state); continue
            except: pass

        # --- 6. VAR CHECK ---
        if eid not in state["var"]:
            try:
                if "var" in str(summary).lower() and ("review" in str(summary).lower() or "checking" in str(summary).lower()):
                    msg=f"🟢 VAR CHECK! 👀\n\n{home} vs {away}\n🏆 {league_name}\n\nVAR is checking... Goal or not? 👇\n\n🟢 FOLLOW for Instant Result!\n\n#VAR {VIRAL_TAGS}"
                    if fb_text(msg): state["var"][eid]=1; posted+=1; save_state(state); continue
            except: pass

        # --- 7. HALF TIME ---
        if status=="STATUS_HALFTIME" and eid not in state["ht"]:
            msg=f"🟢 HALF TIME! ⏸️\n\n{home} {hs} - {as_} {away}\n🏆 {league_name}\n\nWhat did you think of the first half? Rate it /10 👇\n\nSecond half LIVE soon - Stay here!\n\n🟢 FOLLOW Unfiltered Scores!\n\n#HalfTime #{home_short}vs{away_short} {VIRAL_TAGS}"
            if fb_text(msg): state["ht"][eid]=1; posted+=1; save_state(state); continue

        # --- 8. FULL TIME (NEVER as Goal Alert) ---
        if status in ["STATUS_FULL_TIME","STATUS_FINAL","STATUS_FINAL_PEN","STATUS_FINAL_OT"] and eid not in state["ft"]:
            if eid in state["kick"] or eid in state["last"]:
                winner="Draw!"
                if hs>as_: winner=f"{home} WINS! 🎉"
                elif as_>hs: winner=f"{away} WINS! 🎉"
                msg=f"🟢 FULL TIME! ✅\n\n{home} {hs} - {as_} {away}\n🏆 {league_name}\n⏱️ FT - {winner}\n\nWho was your MAN OF THE MATCH? 👇\n\nThanks for following LIVE with us! 🙏\n🟢 FOLLOW Unfiltered Scores for next LIVE game!\n🔔 Turn ON Notifications\n\n#FullTime #{home_short}vs{away_short} #MOTM {VIRAL_TAGS}"
                if fb_text(msg): state["ft"][eid]=1; posted+=1; save_state(state); continue

    except Exception as e:
        print(f"EV ERR {e}"); continue

# --- 9. NEWS + HD PHOTO (WHEN NO LIVE) ---
if posted==0:
    news=get_news()
    random.shuffle(news)
    for title,link,img in news:
        if posted>=2: break
        if link in state["news"]: continue
        # Make news viral
        msg=f"🟢 BREAKING NEWS! 📰🔥\n\n{title}\n\n👉 Full story: {link}\n\nWhat's your take? Comment below! 👇\n\n🟢 FOLLOW Unfiltered Scores for BREAKING Football News 24/7!\n🔔 Turn ON Notifications - Be FIRST to know!\n\n#BreakingNews #FootballNews #TransferNews {VIRAL_TAGS}"
        ok=False
        if img: ok=fb_photo(img, msg)
        if not ok: ok=fb_text(msg)
        if ok:
            state["news"].append(link); posted+=1; save_state(state); time.sleep(3)
            # keep only last 100 news
            if len(state["news"])>100: state["news"]=state["news"][-100:]

print(f"V-ULTIMATE v6 DONE POSTED {posted}")
save_state(state)
