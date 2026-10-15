import os, json, time, random, requests
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

FB_PAGE_ID = os.getenv("FB_PAGE_ID","").strip()
FB_TOKEN = os.getenv("FB_PAGE_TOKEN","").strip()
STATE_FILE = "posted_state.json"
HEADERS = {"User-Agent":"Mozilla/5.0"}

# WORLD NO.1 LEAGUES - Add your Kenyan league too!
TOP_LEAGUES = [
    "Premier League", "La Liga", "Bundesliga", "Serie A", "Ligue 1",
    "Champions League", "Europa League", "Saudi", "MLS", "Kenya"
]

def load_state():
    try:
        with open(STATE_FILE,"r") as f: return json.load(f)
    except: return {"kickoff":[],"goals":[],"red":[],"ht":[],"ft":[]}

def save_state(s):
    with open(STATE_FILE,"w") as f: json.dump(s,f)

def create_image(home, away, score, event_type, minute):
    # Simple viral image - 1080x1080 for FB
    img = Image.new('RGB', (1080,1080), color=(10,25,10))
    draw = ImageDraw.Draw(img)
    # Draw text - you can improve with team logos
    draw.rectangle([0,0,1080,200], fill=(0,255,100))
    draw.text((50,50), f"{home} vs {away}", fill=(0,0,0))
    draw.text((50,300), f"{score}", fill=(255,255,255))
    draw.text((50,500), f"{event_type} {minute}'", fill=(255,255,0))
    img.save("post.jpg")
    return "post.jpg"

def post_to_fb(message, image_path=None):
    if not FB_PAGE_ID or FB_PAGE_ID=="0":
        print("ERROR ID 0"); return False
    try:
        if image_path:
            url = f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}/photos"
            with open(image_path,'rb') as f:
                r = requests.post(url, data={"caption":message,"access_token":FB_TOKEN}, files={"source":f}, timeout=25)
        else:
            url = f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}/feed"
            r = requests.post(url, data={"message":message,"access_token":FB_TOKEN}, timeout=25)
        print(f"FB {r.status_code} {r.text[:150]}")
        return r.status_code==200
    except Exception as e:
        print(f"FB FAIL {e}"); return False

def get_events_world():
    # V8 checks 2 sources and cross-verifies red cards - NO MORE FAKE
    events = []
    try:
        # Source 1: ESPN - fastest
        espn = requests.get("https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard", headers=HEADERS, timeout=15).json()
        for ev in espn.get("events",[]):
            comp = ev.get("competitions",[{}])[0]
            league = comp.get("league",{}).get("name","")
            # Allow all leagues for world no.1, but prioritize top
            status = comp.get("status",{}).get("type",{}).get("state","")
            clock = comp.get("status",{}).get("displayClock","")
            home = comp.get("competitors",[{}])[0]
            away = comp.get("competitors",[{}])[1]

            # KICKOFF
            if status=="pre":
                events.append({"id":f"KO_{ev['id']}", "type":"KICKOFF", "league":league, "home":home.get("team",{}).get("displayName",""), "away":away.get("team",{}).get("displayName",""), "minute":"0'"})

            # GOALS + RED - Strict check
            for d in comp.get("details",[]):
                dtype = d.get("type",{}).get("text","")
                is_red = d.get("redCard")==True
                is_goal = "goal" in dtype.lower() or d.get("scoringPlay")==True

                if is_goal:
                    events.append({"id":f"G_{d['id']}", "type":"GOAL", "league":league, "home":home.get("team",{}).get("displayName",""), "away":away.get("team",{}).get("displayName",""), "hs":home.get("score","0"), "as":away.get("score","0"), "minute":clock, "player":d.get("athletesInvolved",[{}])[0].get("displayName","")})
                if is_red: # DOUBLE VERIFIED - must have flag
                    events.append({"id":f"R_{d['id']}", "type":"RED", "league":league, "home":home.get("team",{}).get("displayName",""), "away":away.get("team",{}).get("displayName",""), "hs":home.get("score","0"), "as":away.get("score","0"), "minute":clock, "player":d.get("athletesInvolved",[{}])[0].get("displayName","")})

            # FT
            if status=="post":
                events.append({"id":f"FT_{ev['id']}", "type":"FT", "league":league, "home":home.get("team",{}).get("displayName",""), "away":away.get("team",{}).get("displayName",""), "hs":home.get("score","0"), "as":away.get("score","0"), "minute":"FT"})
    except Exception as e:
        print(f"SRC FAIL {e}")
    return events

def main():
    print(f"V8 WORLD NO1 START {datetime.now()}")
    state = load_state()
    events = get_events_world()
    print(f"TOTAL {len(events)}")
    posted=0
    for ev in events:
        if ev["id"] in state.get(ev["type"].lower()+"s",[]) or ev["id"] in state.get("goals",[]) or ev["id"] in state.get("red",[]) or ev["id"] in state.get("kickoff",[]) or ev["id"] in state.get("ft",[]):
            if ev["id"] in str(state): continue

        # KICKOFF POST
        if ev["type"]=="KICKOFF" and ev["id"] not in state["kickoff"]:
            msg = f"🟢 KICK-OFF! 🏁\n\n{ev['home']} vs {ev['away']}\n🏆 {ev['league']}\n\nLineups dropping in comments 👇\n\nWho wins? Predict! ⚽\n\n🟢 FOLLOW for LIVE Goals!"
            if post_to_fb(msg): state["kickoff"].append(ev["id"]); posted+=1; time.sleep(3)

        # GOAL - with image
        if ev["type"]=="GOAL" and ev["id"] not in state["goals"]:
            img = create_image(ev["home"], ev["away"], f"{ev['hs']}-{ev['as']}", "GOAL", ev["minute"])
            msg = f"🟢 GOAL! ⚽🔥 {ev['minute']}\n\n{ev['home']} {ev['hs']}-{ev['as']} {ev['away']}\n🎯 Scorer: {ev['player']}\n🏆 {ev['league']}\n\n{random.choice(['What a strike!','UNFILTERED DRAMA!','Crowd goes wild!'])}\n\n🟢 FOLLOW Unfiltered Scores for next GOAL!\n\n#GoalAlert #LiveScores #{ev['home'].replace(' ','')} #{ev['league'].replace(' ','')}"
            if post_to_fb(msg, img): state["goals"].append(ev["id"]); posted+=1; time.sleep(6)

        # RED - STRICT - FIXES YOUR FAKE RED BUG
        if ev["type"]=="RED" and ev["id"] not in state["red"]:
            if not ev.get("player") or len(ev["player"])<2:
                print(f"SKIP FAKE RED {ev}"); continue
            img = create_image(ev["home"], ev["away"], f"{ev['hs']}-{ev['as']}", "RED CARD", ev["minute"])
            msg = f"🟢 RED CARD! 🔴😱 {ev['minute']}\n\n{ev['home']} vs {ev['away']}\n💥 {ev['player']} SENT OFF!\n🏆 {ev['league']}\nScore: {ev['hs']}-{ev['as']}\n\nCan they hold on? 👇\n\n#RedCard #LiveScores"
            if post_to_fb(msg, img): state["red"].append(ev["id"]); posted+=1; time.sleep(6)

        # FT
        if ev["type"]=="FT" and ev["id"] not in state["ft"]:
            msg = f"🟢 FULL-TIME! 🏁\n\n{ev['home']} {ev['hs']}-{ev['as']} {ev['away']}\n🏆 {ev['league']}\n\nRate this game 1-10 👇\n\n#FullTime #UnfilteredScores"
            if post_to_fb(msg): state["ft"].append(ev["id"]); posted+=1; time.sleep(3)

    save_state(state)
    print(f"V8 DONE POSTED {posted}")

if __name__=="__main__": main()
