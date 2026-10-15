import os, json, time, random, requests
from datetime import datetime

FB_PAGE_ID = os.getenv("FB_PAGE_ID","").strip()
FB_TOKEN = os.getenv("FB_PAGE_TOKEN","").strip()
STATE_FILE = "posted_state.json"
HEADERS = {"User-Agent":"Mozilla/5.0"}

def load_state():
    try:
        with open(STATE_FILE,"r") as f: return json.load(f)
    except: return {"kickoff":[],"goals":[],"red":[],"ft":[]}

def save_state(s):
    with open(STATE_FILE,"w") as f: json.dump(s,f)

def post_to_fb(message):
    if not FB_PAGE_ID or FB_PAGE_ID=="0": print("ERROR ID 0"); return False
    url = f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}/feed"
    r = requests.post(url, data={"message":message,"access_token":FB_TOKEN}, timeout=20)
    print(f"FB {r.status_code} {r.text[:150]}")
    return r.status_code==200

def get_live():
    events=[]
    try:
        data = requests.get("https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard", headers=HEADERS, timeout=15).json()
        for ev in data.get("events",[]):
            comp = ev.get("competitions",[{}])[0]
            league = comp.get("league",{}).get("name","Football")
            state = comp.get("status",{}).get("type",{}).get("state","")
            clock = comp.get("status",{}).get("displayClock","")
            home = comp.get("competitors",[])[0]
            away = comp.get("competitors",[])[1]
            hname = home.get("team",{}).get("displayName","Home")
            aname = away.get("team",{}).get("displayName","Away")
            if state=="pre":
                events.append({"id":f"KO_{ev['id']}", "type":"KICKOFF", "league":league, "home":hname, "away":aname})
            for d in comp.get("details",[]):
                if d.get("scoringPlay")==True:
                    events.append({"id":f"G_{d['id']}", "type":"GOAL", "league":league, "home":hname, "away":aname, "hs":home.get("score","0"), "as":away.get("score","0"), "minute":clock, "player":d.get("athletesInvolved",[{}])[0].get("displayName","")})
                if d.get("redCard")==True and d.get("athletesInvolved"):
                    events.append({"id":f"R_{d['id']}", "type":"RED", "league":league, "home":hname, "away":aname, "hs":home.get("score","0"), "as":away.get("score","0"), "minute":clock, "player":d.get("athletesInvolved",[{}])[0].get("displayName","")})
            if state=="post":
                events.append({"id":f"FT_{ev['id']}", "type":"FT", "league":league, "home":hname, "away":aname, "hs":home.get("score","0"), "as":away.get("score","0")})
    except Exception as e: print(f"API FAIL {e}")
    return events

def main():
    print(f"V8 FINAL NO-KEY {datetime.now()}")
    state=load_state()
    evs=get_live()
    print(f"TOTAL {len(evs)}")
    posted=0
    for ev in evs:
        if ev["id"] in state["kickoff"]+state["goals"]+state["red"]+state["ft"]: continue
        if ev["type"]=="KICKOFF":
            if post_to_fb(f"🟢 KICK-OFF! 🏁\n\n{ev['home']} vs {ev['away']}\n🏆 {ev['league']}\n\nWho wins? 👇\n\n🟢 FOLLOW for LIVE Goals!"): state["kickoff"].append(ev["id"]); posted+=1; time.sleep(2)
        if ev["type"]=="GOAL" and ev["id"] not in state["goals"]:
            if post_to_fb(f"🟢 GOAL! ⚽ {ev['minute']}\n\n{ev['home']} {ev['hs']}-{ev['as']} {ev['away']}\n🎯 {ev['player']}\n🏆 {ev['league']}\n\n🔥 UNFILTERED!\n\n🟢 FOLLOW Unfiltered Scores!"): state["goals"].append(ev["id"]); posted+=1; time.sleep(4)
        if ev["type"]=="RED" and ev["id"] not in state["red"]:
            if len(ev.get("player",""))<2: continue
            if post_to_fb(f"🟢 RED CARD! 🔴 {ev['minute']}\n\n{ev['home']} vs {ev['away']}\n💥 {ev['player']} SENT OFF! {ev['hs']}-{ev['as']}"): state["red"].append(ev["id"]); posted+=1; time.sleep(4)
        if ev["type"]=="FT" and ev["id"] not in state["ft"]:
            if post_to_fb(f"🟢 FULL-TIME! 🏁\n\n{ev['home']} {ev['hs']}-{ev['as']} {ev['away']}\n🏆 {ev['league']}"): state["ft"].append(ev["id"]); posted+=1
    save_state(state)
    print(f"DONE POSTED {posted}")

if __name__=="__main__": main()
