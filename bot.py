import os, json, time, random, requests, xml.etree.ElementTree as ET
from datetime import datetime

FB_PAGE_ID = os.getenv("FB_PAGE_ID","").strip()
FB_TOKEN = os.getenv("FB_PAGE_TOKEN","").strip()
STATE_FILE = "posted_state.json"
HEADERS = {
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept":"application/json",
    "Referer":"https://www.livescore.com/"
}
MAX_PER_RUN = 15

def load_state():
    default = {"kickoff":[],"goals":[],"red":[],"ft":[],"news":[]}
    try:
        with open(STATE_FILE,"r") as f:
            data = json.load(f)
            if isinstance(data, dict):
                for k in default:
                    if k not in data: data[k]=[]
                for k in data: data[k]=data[k][-150:]
                return data
    except: pass
    return default

def save_state(s):
    try:
        for k in s: s[k]=s[k][-150:]
        with open(STATE_FILE,"w") as f: json.dump(s,f)
    except: pass

def post_to_fb(message):
    try:
        if not FB_PAGE_ID or FB_PAGE_ID=="0": return False
        url = f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}/feed"
        r = requests.post(url, data={"message":message,"access_token":FB_TOKEN}, timeout=20)
        print(f"FB {r.status_code} {r.text[:200]}")
        return r.status_code==200
    except: return False

def get_live_from_livescore():
    """
    Livescore private API - used by their own website/app
    Returns live matches with scores, goals, minute
    """
    events=[]
    seen=set()
    urls = [
        "https://prod-public-api.livescore.com/v1/api/react/stage/soccer/live.json?MD=1",
        "https://prod-public-api.livescore.com/v1/api/app/stage/soccer/live",
    ]
    for api_url in urls:
        try:
            print(f"Trying Livescore {api_url}")
            r = requests.get(api_url, headers=HEADERS, timeout=15)
            print(f"Livescore status {r.status_code} len {len(r.text)}")
            if r.status_code!=200: continue
            data = r.json()
            # Structure: Stages -> Events ->...
            stages = data.get("Stages",[]) or data.get("stages",[]) or []
            if not stages and "data" in data:
                stages = data["data"].get("Stages",[])

            for stage in stages:
                comp_name = stage.get("Cnm","Football") + " - " + stage.get("Snm","")
                league = stage.get("Cnm","") or stage.get("Snm","Football")
                for ev in stage.get("Events",[]) or stage.get("events",[]) or []:
                    try:
                        eid = str(ev.get("Eid") or ev.get("eid") or ev.get("id"))
                        if not eid: continue
                        home = ev.get("T1",[{}])[0].get("Nm","Home") if isinstance(ev.get("T1"),list) else ev.get("home","Home")
                        away = ev.get("T2",[{}])[0].get("Nm","Away") if isinstance(ev.get("T2"),list) else ev.get("away","Away")
                        # Scores
                        tr1 = ev.get("Tr1","0") # home score
                        tr2 = ev.get("Tr2","0") # away score
                        # Status
                        esd = ev.get("Esd") # match minute/status
                        ecd = ev.get("Ecd") # status code
                        # Ecd: 0 not started, 1 live, 2 HT, 3 FT etc
                        minute = ev.get("Epr",0) # minute
                        status = ev.get("Eps","") # e.g. "HT", "FT"

                        # Build unique keys
                        if ecd==0 or ecd=="0": # Not started -> Kickoff if within few mins? Livescore live endpoint only has live, so skip
                            continue

                        # GOAL detection - we track score changes via Tr1/Tr2
                        # Livescore API does not give individual goal events in live.json, only current score
                        # So we create goal event from score
                        key_goal = f"G_{eid}_{tr1}_{tr2}"
                        key_ft = f"FT_{eid}_{tr1}_{tr2}"
                        key_kick = f"KO_{eid}"

                        # If match is live and score changed, it's a goal
                        if str(ecd)=="1" or str(status).find("Live")>=0 or minute>0:
                            # Check if this score already seen as goal
                            if key_goal not in seen:
                                seen.add(key_goal)
                                # Avoid posting 0-0 as goal
                                if not (tr1=="0" and tr2=="0"):
                                    events.append({
                                        "id": key_goal,
                                        "type":"GOAL",
                                        "league": league,
                                        "home": home,
                                        "away": away,
                                        "hs": tr1,
                                        "as": tr2,
                                        "minute": f"{minute}'" if minute else status or "LIVE",
                                        "player": "" # Livescore live.json doesn't give scorer in this endpoint, we add later from details API
                                    })
                        # FT detection
                        if status=="FT" or ecd==3 or status=="FT" or str(esd).find("FT")>=0:
                            if key_ft not in seen:
                                seen.add(key_ft)
                                events.append({"id":key_ft,"type":"FT","league":league,"home":home,"away":away,"hs":tr1,"as":tr2})

                    except Exception as ex:
                        print(f"Parse event fail {ex}")
                        continue
            if events:
                break # Got events from first working URL
        except Exception as e:
            print(f"Livescore API FAIL {e}")
            continue

    # If Livescore main API failed or gave 0 events, try backup API-Sports style or ESPN as fallback
    if not events:
        print("Livescore live 0 events, trying ESPN fallback for now...")
        # Fallback to ESPN just to keep bot alive, you can remove later
        try:
            data = requests.get("https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard", headers=HEADERS, timeout=15).json()
            for ev in data.get("events",[]):
                eid = ev.get("id")
                comp = ev.get("competitions",[{}])[0]
                league = comp.get("league",{}).get("name","Football")
                comps = comp.get("competitors",[])
                if len(comps)<2: continue
                hname = comps[0].get("team",{}).get("displayName","Home")
                aname = comps[1].get("team",{}).get("displayName","Away")
                hscore = comps[0].get("score","0")
                ascore = comps[1].get("score","0")
                state = comp.get("status",{}).get("type",{}).get("state","")
                if state=="post":
                    events.append({"id":f"FT_{eid}_{hscore}_{ascore}","type":"FT","league":league,"home":hname,"away":aname,"hs":hscore,"as":ascore})
        except: pass

    return events

def get_news_all_sources():
    news=[]
    sources = [
        ("https://feeds.bbci.co.uk/sport/football/rss.xml", "BBC"),
        ("https://www.skysports.com/rss/11095", "Sky Sports"),
        ("https://www.espn.com/espn/rss/soccer/news", "ESPN"),
        ("https://www.goal.com/en/feeds/news?fmt=rss", "Goal"),
    ]
    for url, name in sources:
        try:
            rss = requests.get(url, headers=HEADERS, timeout=12).text
            root = ET.fromstring(rss)
            for item in root.findall(".//item")[:5]:
                title = item.find("title").text.strip() if item.find("title") is not None else ""
                link = item.find("link").text.strip() if item.find("link") is not None else ""
                if title and len(title)>15:
                    news.append({"id":link, "title":title, "source":name})
        except: continue
    random.shuffle(news)
    return news

def main():
    print(f"V11 LIVESCORE EDITION {datetime.now()}")
    state=load_state()
    evs=get_live_from_livescore()
    print(f"LIVESCORE EVENTS {len(evs)}")
    posted=0
    all_ids=[]
    for k in ["kickoff","goals","red","ft"]: all_ids+=state.get(k,[])

    for ev in evs:
        if posted>=MAX_PER_RUN: break
        if ev["id"] in all_ids:
            print(f"SKIP DUP {ev['id']}")
            continue
        ok=False
        if ev["type"]=="GOAL":
            # Try to get scorer from Livescore details API (optional)
            scorer = ev.get("player","")
            scorer_text = f"🎯 Scorer: {scorer}\n" if scorer else ""
            ok=post_to_fb(f"🟢 GOAL! ⚽ {ev['minute']}\n\n{ev['home']} {ev['hs']}-{ev['as']} {ev['away']}\n{scorer_text}🏆 {ev['league']}\n\n⚡ LIVE from LiveScore! Follow for next goal!")
            if ok: state["goals"].append(ev["id"]); posted+=1
        elif ev["type"]=="FT":
            ok=post_to_fb(f"🟢 FULL-TIME! 🏁\n\n{ev['home']} {ev['hs']}-{ev['as']} {ev['away']}\n🏆 {ev['league']}\n\nRate this game 1-10 👇\n\n🟢 FOLLOW Unfiltered Scores!")
            if ok: state["ft"].append(ev["id"]); posted+=1
        if ok: time.sleep(3)

    # NON-STOP NEWS - 2 if no games, 1 if games
    try:
        fresh_news = get_news_all_sources()
        news_to_post = 2 if len(evs)==0 else 1
        count=0
        for n in fresh_news:
            if count>=news_to_post or posted>=MAX_PER_RUN: break
            if n["id"] in state.get("news",[]): continue
            if post_to_fb(f"🟢 BREAKING! 📰🔥\n\n{n['title']}\n\nSource: {n['source']}\n\nThoughts? 👇\n\n🟢 FOLLOW Unfiltered Scores 24/7!"):
                state["news"].append(n["id"]); posted+=1; count+=1; time.sleep(3)
        if count==0 and fresh_news and posted<MAX_PER_RUN:
            n=random.choice(fresh_news)
            post_to_fb(f"🟢 FOOTBALL UPDATE! 🔥\n\n{n['title']}\n\nVia {n['source']}\n\n#UnfilteredScores")
            posted+=1
    except Exception as e:
        print(f"NEWS ERR {e}")

    save_state(state)
    print(f"DONE POSTED {posted}")

if __name__=="__main__":
    main()
