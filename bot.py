import os, json, time, requests
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
    if not FB_PAGE_ID or FB_PAGE_ID=="0":
        print("ERROR PAGE ID 0"); return False
    url = f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}/feed"
    r = requests.post(url, data={"message":message,"access_token":FB_TOKEN}, timeout=20)
    print(f"FB {r.status_code} {r.text[:200]}")
    return r.status_code==200

def get_live():
    events=[]
    try:
        url = "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard"
        # eng.1 = EPL = always has data. Then we also get all leagues
        urls = [
            "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard",
            "https://site.api.espn.com/apis/site/v2/sports/soccer/esp.1/scoreboard",
            "https://site.api.espn.com/apis/site/v2/sports/soccer/ger.1/scoreboard",
            "https://site.api.espn.com/apis/site/v2/sports/soccer/ita.1/scoreboard",
            "https://site.api.espn.com/apis/site/v2/sports/soccer/fra.1/scoreboard",
            "https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/scoreboard",
            "https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.europa/scoreboard"
        ]
        for api_url in urls:
            try:
                data = requests.get(api_url, headers=HEADERS, timeout=15).json()
                for ev in data.get("events",[]):
                    try:
                        eid = ev.get("id") or ev.get("uid") or str(hash(str(ev)))
                        comp = ev.get("competitions",[{}])[0]
                        if not comp: continue
                        league = comp.get("league",{}).get("name","Football")
                        status = comp.get("status",{}).get("type",{}).get("state","")
                        clock = comp.get("status",{}).get("displayClock","")
                        comps = comp.get("competitors",[])
                        if len(comps)<2: continue
                        home = comps[0]
                        away = comps[1]
                        hname = home.get("team",{}).get("displayName","Home")
                        aname = away.get("team",{}).get("displayName","Away")
                        hscore = home.get("score","0")
                        ascore = away.get("score","0")

                        if status=="pre":
                            events.append({"id":f"KO_{eid}", "type":"KICKOFF", "league":league, "home":hname, "away":aname})

                        # details = goals / reds
                        for d in comp.get("details",[]):
                            try:
                                did = d.get("id") or d.get("clock") or str(d)
                                if d.get("scoringPlay")==True:
                                    player = ""
                                    ath = d.get("athletesInvolved",[])
                                    if ath and len(ath)>0: player = ath[0].get("displayName","")
                                    events.append({"id":f"G_{eid}_{did}", "type":"GOAL", "league":league, "home":hname, "away":aname, "hs":hscore, "as":ascore, "minute":clock or d.get("clock",""), "player":player})
                                if d.get("redCard")==True:
                                    ath = d.get("athletesInvolved",[])
                                    player = ath[0].get("displayName","") if ath else ""
                                    if player:
                                        events.append({"id":f"R_{eid}_{did}", "type":"RED", "league":league, "home":hname, "away":aname, "hs":hscore, "as":ascore, "minute":clock or d.get("clock",""), "player":player})
                            except: continue

                        if status=="post":
                            events.append({"id":f"FT_{eid}", "type":"FT", "league":league, "home":hname, "away":aname, "hs":hscore, "as":ascore})
                    except Exception as inner_e:
                        print(f"Skip one game {inner_e}")
                        continue
            except Exception as e:
                print(f"URL fail {api_url} {e}")
                continue
    except Exception as e:
        print(f"API FAIL {e}")
    return events

def main():
    print(f"V9 FIXED NO-KEY {datetime.now()}")
    state=load_state()
    evs=get_live()
    print(f"TOTAL {len(evs)}")
    if len(evs)==0:
        print("No live games right now - normal if night time")
    posted=0
    for ev in evs:
        all_ids = state["kickoff"]+state["goals"]+state["red"]+state["ft"]
        if ev["id"] in all_ids: continue

        if ev["type"]=="KICKOFF":
            msg=f"🟢 KICK-OFF! 🏁\n\n{ev['home']} vs {ev['away']}\n🏆 {ev['league']}\n\nWho wins? Predict 👇\n\n🟢 FOLLOW for LIVE Goals!"
            if post_to_fb(msg): state["kickoff"].append(ev["id"]); posted+=1; time.sleep(2)

        if ev["type"]=="GOAL":
            msg=f"🟢 GOAL! ⚽ {ev['minute']}\n\n{ev['home']} {ev['hs']}-{ev['as']} {ev['away']}\n🎯 {ev['player']}\n🏆 {ev['league']}\n\n🔥 UNFILTERED!\n\n🟢 FOLLOW Unfiltered Scores!"
            if post_to_fb(msg): state["goals"].append(ev["id"]); posted+=1; time.sleep(4)

        if ev["type"]=="RED":
            if len(ev.get("player",""))<2: continue
            msg=f"🟢 RED CARD! 🔴 {ev['minute']}\n\n{ev['home']} vs {ev['away']}\n💥 {ev['player']} SENT OFF! {ev['hs']}-{ev['as']}\n🏆 {ev['league']}"
            if post_to_fb(msg): state["red"].append(ev["id"]); posted+=1; time.sleep(4)

        if ev["type"]=="FT":
            msg=f"🟢 FULL-TIME! 🏁\n\n{ev['home']} {ev['hs']}-{ev['as']} {ev['away']}\n🏆 {ev['league']}\n\nRate 1-10 👇"
            if post_to_fb(msg): state["ft"].append(ev["id"]); posted+=1

    save_state(state)
    print(f"DONE POSTED {posted}")

if __name__=="__main__": main()
