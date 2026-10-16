import os, json, time, random, requests, xml.etree.ElementTree as ET
from datetime import datetime

FB_PAGE_ID = os.getenv("FB_PAGE_ID","").strip()
FB_TOKEN = os.getenv("FB_PAGE_TOKEN","").strip()
STATE_FILE = "posted_state.json"
HEADERS = {"User-Agent":"Mozilla/5.0","Accept":"application/json","Referer":"https://www.livescore.com/"}
MAX_PER_RUN = 5
DELAY_BETWEEN = 65
SPAM_STOP = False

def load_state():
    default = {"kickoff":[],"goals":[],"red":[],"ft":[],"news":[]}
    try:
        with open(STATE_FILE,"r") as f:
            d=json.load(f)
            for k in default:
                if k not in d: d[k]=[]
                d[k]=d[k][-200:]
            return d
    except: return default

def save_state(s):
    try:
        for k in s: s[k]=s[k][-200:]
        with open(STATE_FILE,"w") as f: json.dump(s,f)
    except: pass

def post_to_fb(message):
    global SPAM_STOP
    try:
        if not FB_PAGE_ID or FB_PAGE_ID=="0": return False
        url = f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}/feed"
        r = requests.post(url, data={"message":message,"access_token":FB_TOKEN}, timeout=20)
        txt=r.text
        print(f"FB {r.status_code} {txt[:300]}")
        if r.status_code==200: return True
        if "We limit how often" in txt or "spam" in txt.lower():
            print("!!! SPAM LIMIT HIT - STOPPING!!!")
            SPAM_STOP=True
            return False
        return False
    except: return False

def get_live():
    events=[]
    seen=set()
    # 1. TRY LIVESCORE FIRST (you asked)
    try:
        r=requests.get("https://prod-public-api.livescore.com/v1/api/react/stage/soccer/live.json?MD=1", headers=HEADERS, timeout=15)
        if r.status_code==200:
            data=r.json()
            for stage in data.get("Stages",[]):
                league=stage.get("Cnm","Football")
                for ev in stage.get("Events",[]):
                    try:
                        eid=str(ev.get("Eid"))
                        home=ev.get("T1",[{}])[0].get("Nm","Home")
                        away=ev.get("T2",[{}])[0].get("Nm","Away")
                        tr1=str(ev.get("Tr1","0"))
                        tr2=str(ev.get("Tr2","0"))
                        minute=ev.get("Epr",0)
                        ecd=ev.get("Ecd")
                        status=ev.get("Eps","")
                        if ecd==1 and not (tr1=="0" and tr2=="0"):
                            key=f"G_{eid}_{tr1}_{tr2}"
                            if key not in seen:
                                events.append({"id":key,"type":"GOAL","league":league,"home":home,"away":away,"hs":tr1,"as":tr2,"minute":f"{minute}'" if minute else status})
                                seen.add(key)
                        if status=="FT" or ecd==3:
                            key=f"FT_{eid}_{tr1}_{tr2}"
                            if key not in seen:
                                events.append({"id":key,"type":"FT","league":league,"home":home,"away":away,"hs":tr1,"as":tr2})
                                seen.add(key)
                    except: continue
    except Exception as e:
        print(f"Livescore fail {e}")

    # 2. ESPN FALLBACK + ADDS KICKOFF + RED CARD + DETAILED SCORER (important things you had)
    try:
        for api_url in [
            "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard",
            "https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard"
        ]:
            data=requests.get(api_url, headers=HEADERS, timeout=15).json()
            for ev in data.get("events",[]):
                eid=ev.get("id")
                comp=ev.get("competitions",[{}])[0]
                if not comp: continue
                league=comp.get("league",{}).get("name","Football")
                st_type=comp.get("status",{}).get("type",{}).get("state","")
                clock=comp.get("status",{}).get("displayClock","")
                comps=comp.get("competitors",[])
                if len(comps)<2: continue
                hname=comps[0].get("team",{}).get("displayName","Home")
                aname=comps[1].get("team",{}).get("displayName","Away")
                hscore=comps[0].get("score","0")
                ascore=comps[1].get("score","0")

                if st_type=="pre":
                    kid=f"KO_{eid}"
                    if kid not in seen:
                        events.append({"id":kid,"type":"KICKOFF","league":league,"home":hname,"away":aname})
                        seen.add(kid)

                seen_score=set()
                for d in comp.get("details",[]):
                    if d.get("scoringPlay"):
                        # FIX DUPLICATE - use score not detail id
                        sk=f"{eid}_{hscore}_{ascore}"
                        if sk in seen_score: continue
                        seen_score.add(sk)
                        gid=f"G_{eid}_{hscore}_{ascore}"
                        if gid in seen: continue
                        player=""
                        if d.get("athletesInvolved"): player=d["athletesInvolved"][0].get("displayName","")
                        events.append({"id":gid,"type":"GOAL","league":league,"home":hname,"away":aname,"hs":hscore,"as":ascore,"minute":clock or d.get("clock",""),"player":player})
                        seen.add(gid)

                    if d.get("redCard"):
                        player=""
                        if d.get("athletesInvolved"): player=d["athletesInvolved"][0].get("displayName","")
                        if player:
                            rid=f"R_{eid}_{player}"
                            if rid not in seen:
                                events.append({"id":rid,"type":"RED","league":league,"home":hname,"away":aname,"hs":hscore,"as":ascore,"minute":clock or d.get("clock",""),"player":player})
                                seen.add(rid)

                if st_type=="post":
                    fid=f"FT_{eid}_{hscore}_{ascore}"
                    if fid not in seen:
                        events.append({"id":fid,"type":"FT","league":league,"home":hname,"away":aname,"hs":hscore,"as":ascore})
                        seen.add(fid)
    except Exception as e:
        print(f"ESPN fallback fail {e}")

    return events

def get_news():
    news=[]
    sources=[
        ("https://feeds.bbci.co.uk/sport/football/rss.xml","BBC"),
        ("https://www.skysports.com/rss/11095","Sky Sports"),
        ("https://www.espn.com/espn/rss/soccer/news","ESPN"),
        ("https://www.goal.com/en/feeds/news?fmt=rss","Goal"),
        ("https://talksport.com/football/feed/","TalkSport"),
    ]
    for url,name in sources:
        try:
            rss=requests.get(url, headers=HEADERS, timeout=12).text
            root=ET.fromstring(rss)
            for item in root.findall(".//item")[:4]:
                t=item.find("title")
                l=item.find("link")
                if t is None or l is None: continue
                title=t.text.strip()
                link=l.text.strip()
                if len(title)>15:
                    news.append({"id":link,"title":title,"source":name})
        except: continue
    random.shuffle(news)
    return news

def main():
    global SPAM_STOP
    print(f"V14 FINAL ALL-FEATURES 5-PER-RUN {datetime.now()}")
    state=load_state()
    evs=get_live()
    print(f"TOTAL EVENTS {len(evs)}")
    posted=0
    all_ids=[]
    for k in state: all_ids+=state[k]

    # Post live events first - priority GOAL > RED > FT > KICKOFF
    evs_sorted = sorted(evs, key=lambda x: {"GOAL":0,"RED":1,"FT":2,"KICKOFF":3}.get(x["type"],4))

    for ev in evs_sorted:
        if posted>=MAX_PER_RUN or SPAM_STOP: break
        if ev["id"] in all_ids: continue

        msg=""
        if ev["type"]=="KICKOFF":
            msg=f"🟢 KICK-OFF! 🏁\n\n{ev['home']} vs {ev['away']}\n🏆 {ev['league']}\n\nWho wins? Predict score 👇\n\n🟢 FOLLOW Unfiltered Scores for LIVE Goals!\n\n#LiveScores #FootballLive"
        elif ev["type"]=="GOAL":
            scorer_line = f"🎯 Scorer: {ev.get('player','')}\n" if ev.get('player') else ""
            msg=f"🟢 GOAL! ⚽ {ev['minute']}\n\n{ev['home']} {ev['hs']}-{ev['as']} {ev['away']}\n{scorer_line}🏆 {ev['league']}\n\n🔥 UNFILTERED! Follow for next goal!\n\n#Goal #LiveScores"
        elif ev["type"]=="RED":
            msg=f"🟢 RED CARD! 🔴 {ev['minute']}\n\n{ev['home']} vs {ev['away']}\n💥 {ev['player']} SENT OFF!\nScore {ev['hs']}-{ev['as']}\n🏆 {ev['league']}\n\n#RedCard"
        elif ev["type"]=="FT":
            msg=f"🟢 FULL-TIME! 🏁\n\n{ev['home']} {ev['hs']}-{ev['as']} {ev['away']}\n🏆 {ev['league']}\n\nRate this game 1-10 👇\n\n🟢 FOLLOW Unfiltered Scores for more LIVE!\n\n#FullTime #FootballNews"

        if msg and post_to_fb(msg):
            state[ev["type"].lower() if ev["type"].lower() in state else "ft" if ev["type"]=="FT" else "goals" if ev["type"]=="GOAL" else "kickoff" if ev["type"]=="KICKOFF" else "red"].append(ev["id"])
            if ev["type"]=="KICKOFF": state["kickoff"].append(ev["id"])
            elif ev["type"]=="GOAL": state["goals"].append(ev["id"])
            elif ev["type"]=="RED": state["red"].append(ev["id"])
            else: state["ft"].append(ev["id"])
            posted+=1
            if posted < MAX_PER_RUN:
                time.sleep(DELAY_BETWEEN)
        if SPAM_STOP: break

    # Fill remaining slots with NEWS - so page never sleeps
    if posted < MAX_PER_RUN and not SPAM_STOP:
        for n in get_news():
            if posted>=MAX_PER_RUN or SPAM_STOP: break
            if n["id"] in state["news"]: continue
            if post_to_fb(f"🟢 BREAKING! 📰🔥\n\n{n['title']}\n\nSource: {n['source']}\n\nDrop your thoughts 👇\n\n🟢 FOLLOW Unfiltered Scores — LIVE Goals + Breaking News 24/7!\n\n#BreakingNews #FootballNews #UnfilteredScores"):
                state["news"].append(n["id"])
                posted+=1
                if posted < MAX_PER_RUN:
                    time.sleep(DELAY_BETWEEN)

    save_state(state)
    print(f"DONE POSTED {posted}/{MAX_PER_RUN} - SUCCESS")

if __name__=="__main__":
    main()
