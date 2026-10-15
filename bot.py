import os, json, time, requests
from datetime import datetime

FB_PAGE_ID = os.getenv("FB_PAGE_ID","").strip()
FB_TOKEN = os.getenv("FB_PAGE_TOKEN","").strip()
STATE_FILE = "posted_state.json"
HEADERS = {"User-Agent":"Mozilla/5.0"}

def load_state():
    default = {"kickoff":[],"goals":[],"red":[],"ft":[]}
    try:
        with open(STATE_FILE,"r") as f:
            data = json.load(f)
            # FIX OLD FILE - add missing keys
            if isinstance(data, dict):
                for k in default:
                    if k not in data:
                        data[k] = []
                return data
            # if old file was list like ["id1","id2"]
            if isinstance(data, list):
                default["goals"] = data
                return default
    except: pass
    return default

def save_state(s):
    with open(STATE_FILE,"w") as f: json.dump(s,f)

def post_to_fb(message):
    if not FB_PAGE_ID or FB_PAGE_ID=="0": return False
    url = f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}/feed"
    r = requests.post(url, data={"message":message,"access_token":FB_TOKEN}, timeout=20)
    print(f"FB {r.status_code} {r.text[:150]}")
    return r.status_code==200

def get_live():
    events=[]
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
                    state = comp.get("status",{}).get("type",{}).get("state","")
                    clock = comp.get("status",{}).get("displayClock","")
                    comps = comp.get("competitors",[])
                    if len(comps)<2: continue
                    home, away = comps[0], comps[1]
                    hname = home.get("team",{}).get("displayName","Home")
                    aname = away.get("team",{}).get("displayName","Away")
                    hscore = home.get("score","0")
                    ascore = away.get("score","0")

                    if state=="pre":
                        events.append({"id":f"KO_{eid}", "type":"KICKOFF", "league":league, "home":hname, "away":aname})
                    for d in comp.get("details",[]):
                        did = d.get("id") or d.get("clock") or str(hash(str(d)))
                        if d.get("scoringPlay")==True:
                            ath = d.get("athletesInvolved",[])
                            player = ath[0].get("displayName","") if ath else ""
                            events.append({"id":f"G_{eid}_{did}", "type":"GOAL", "league":league, "home":hname, "away":aname, "hs":hscore, "as":ascore, "minute":clock or d.get("clock",""), "player":player})
                        if d.get("redCard")==True:
                            ath = d.get("athletesInvolved",[])
                            player = ath[0].get("displayName","") if ath else ""
                            if player:
                                events.append({"id":f"R_{eid}_{did}", "type":"RED", "league":league, "home":hname, "away":aname, "hs":hscore, "as":ascore, "minute":clock or d.get("clock",""), "player":player})
                    if state=="post":
                        events.append({"id":f"FT_{eid}", "type":"FT", "league":league, "home":hname, "away":aname, "hs":hscore, "as":ascore})
                except: continue
        except: continue
    return events

def main():
    print(f"V10 FIXED STATE {datetime.now()}")
    state=load_state()
    print(f"State keys: {list(state.keys())}")
    evs=get_live()
    print(f"TOTAL {len(evs)}")
    posted=0
    # SAFE get all ids
    all_ids = []
    for k in ["kickoff","goals","red","ft"]:
        all_ids += state.get(k,[])

    for ev in evs:
        if ev["id"] in all_ids: continue
        ok=False
        if ev["type"]=="KICKOFF":
            ok=post_to_fb(f"🟢 KICK-OFF! 🏁\n\n{ev['home']} vs {ev['away']}\n🏆 {ev['league']}\n\nWho wins? 👇\n\n🟢 FOLLOW for LIVE Goals!")
            if ok: state["kickoff"].append(ev["id"]); posted+=1
        elif ev["type"]=="GOAL":
            ok=post_to_fb(f"🟢 GOAL! ⚽ {ev['minute']}\n\n{ev['home']} {ev['hs']}-{ev['as']} {ev['away']}\n🎯 {ev['player']}\n🏆 {ev['league']}\n\n🔥 UNFILTERED!")
            if ok: state["goals"].append(ev["id"]); posted+=1
        elif ev["type"]=="RED":
            ok=post_to_fb(f"🟢 RED CARD! 🔴 {ev['minute']}\n\n{ev['home']} vs {ev['away']}\n💥 {ev['player']} SENT OFF! {ev['hs']}-{ev['as']}\n🏆 {ev['league']}")
            if ok: state["red"].append(ev["id"]); posted+=1
        elif ev["type"]=="FT":
            ok=post_to_fb(f"🟢 FULL-TIME! 🏁\n\n{ev['home']} {ev['hs']}-{ev['as']} {ev['away']}\n🏆 {ev['league']}")
            if ok: state["ft"].append(ev["id"]); posted+=1
        if ok: time.sleep(3)

    save_state(state)
    print(f"DONE POSTED {posted}")

if __name__=="__main__": main()
