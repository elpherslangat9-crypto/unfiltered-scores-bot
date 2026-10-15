import os, json, time, requests, xml.etree.ElementTree as ET
from datetime import datetime

FB_PAGE_ID = os.getenv("FB_PAGE_ID","").strip()
FB_TOKEN = os.getenv("FB_PAGE_TOKEN","").strip()
STATE_FILE = "posted_state.json"
HEADERS = {"User-Agent":"Mozilla/5.0"}
MAX_PER_RUN = 15 # BOSS LOVES SPEED - 15 posts allowed per run

def load_state():
    default = {"kickoff":[],"goals":[],"red":[],"ft":[],"news":[]}
    try:
        with open(STATE_FILE,"r") as f:
            data = json.load(f)
            if isinstance(data, dict):
                for k in default:
                    if k not in data:
                        data[k]=[]
                return data
            if isinstance(data, list):
                default["goals"]=data
                return default
    except: pass
    return default

def save_state(s):
    try:
        with open(STATE_FILE,"w") as f:
            json.dump(s,f)
        print(f"STATE SAVED {len(str(s))} bytes")
    except Exception as e:
        print(f"SAVE FAIL {e}")

def post_to_fb(message):
    try:
        if not FB_PAGE_ID or FB_PAGE_ID=="0":
            print("PAGE ID 0"); return False
        url = f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}/feed"
        r = requests.post(url, data={"message":message,"access_token":FB_TOKEN}, timeout=20)
        print(f"FB {r.status_code} {r.text[:200]}")
        return r.status_code==200
    except Exception as e:
        print(f"FB ERROR {e}")
        return False

def get_live():
    events=[]
    urls = [
        "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard",
        "https://site.api.espn.com/apis/site/v2/sports/soccer/esp.1/scoreboard",
        "https://site.api.espn.com/apis/site/v2/sports/soccer/ger.1/scoreboard",
        "https://site.api.espn.com/apis/site/v2/sports/soccer/ita.1/scoreboard",
        "https://site.api.espn.com/apis/site/v2/sports/soccer/fra.1/scoreboard",
        "https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/scoreboard",
        "https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.europa/scoreboard",
        "https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard",
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
        except Exception as e:
            print(f"URL fail {api_url[:40]} {e}")
            continue
    return events

def get_news_all_sources():
    news=[]
    sources = [
        ("https://feeds.bbci.co.uk/sport/football/rss.xml", "BBC"),
        ("https://www.skysports.com/rss/11095", "Sky Sports"),
        ("https://www.espn.com/espn/rss/soccer/news", "ESPN"),
        ("https://talksport.com/football/feed/", "TalkSport"),
        ("https://www.goal.com/en/feeds/news?fmt=rss", "Goal"),
    ]
    for url, name in sources:
        try:
            rss = requests.get(url, headers=HEADERS, timeout=10).text
            root = ET.fromstring(rss)
            for item in root.findall(".//item")[:3]:
                title_el = item.find("title")
                link_el = item.find("link")
                if title_el is None or link_el is None: continue
                title = title_el.text
                link = link_el.text
                if not title or len(title)<15: continue
                news.append({"id":link, "title":title, "source":name})
        except Exception as e:
            print(f"NEWS FAIL {name} {e}")
            continue
    return news

def main():
    print(f"V8 HIGH-VOLUME + NEWS WORLD NO.1 {datetime.now()}")
    state=load_state()
    print(f"State keys {list(state.keys())} kickoff:{len(state.get('kickoff',[]))} goals:{len(state.get('goals',[]))} news:{len(state.get('news',[]))}")

    evs=get_live()
    print(f"TOTAL LIVE EVENTS {len(evs)}")
    posted=0

    all_ids = []
    for k in ["kickoff","goals","red","ft"]:
        all_ids += state.get(k,[])

    for ev in evs:
        if posted >= MAX_PER_RUN:
            print(f"MAX {MAX_PER_RUN} REACHED")
            break
        if ev["id"] in all_ids: continue

        ok=False
        try:
            if ev["type"]=="KICKOFF":
                ok=post_to_fb(f"🟢 KICK-OFF! 🏁\n\n{ev['home']} vs {ev['away']}\n🏆 {ev['league']}\n\nWho wins? Predict score 👇\n\n🟢 FOLLOW Unfiltered Scores for LIVE Goals!")
                if ok: state["kickoff"].append(ev["id"]); posted+=1

            elif ev["type"]=="GOAL":
                ok=post_to_fb(f"🟢 GOAL! ⚽ {ev['minute']}\n\n{ev['home']} {ev['hs']}-{ev['as']} {ev['away']}\n🎯 Scorer: {ev['player']}\n🏆 {ev['league']}\n\n🔥 UNFILTERED! Follow for next goal!")
                if ok: state["goals"].append(ev["id"]); posted+=1

            elif ev["type"]=="RED":
                if len(ev.get("player",""))<2: continue
                ok=post_to_fb(f"🟢 RED CARD! 🔴 {ev['minute']}\n\n{ev['home']} vs {ev['away']}\n💥 {ev['player']} SENT OFF!\nScore {ev['hs']}-{ev['as']}\n🏆 {ev['league']}\n\nGame changed!")
                if ok: state["red"].append(ev["id"]); posted+=1

            elif ev["type"]=="FT":
                ok=post_to_fb(f"🟢 FULL-TIME! 🏁\n\n{ev['home']} {ev['hs']}-{ev['as']} {ev['away']}\n🏆 {ev['league']}\n\nRate this game 1-10 👇\n\n🟢 FOLLOW for more!")
                if ok: state["ft"].append(ev["id"]); posted+=1

            if ok:
                time.sleep(3)
        except Exception as e:
            print(f"POST LOOP ERROR {e}")
            continue

    # --- NEWS PART - 1 news per run to keep speed but not spam ---
    if posted < MAX_PER_RUN:
        try:
            fresh_news = get_news_all_sources()
            print(f"NEWS FOUND {len(fresh_news)}")
            for n in fresh_news:
                if n["id"] in state.get("news",[]): continue
                msg = f"""🟢 BREAKING NEWS! 📰🔥

{n['title']}

Source: {n['source']}

Your thoughts? 👇

🟢 FOLLOW Unfiltered Scores for LIVE Goals + Breaking News!

#FootballNews #Breaking #UnfilteredScores"""
                if post_to_fb(msg):
                    state["news"].append(n["id"])
                    posted+=1
                    time.sleep(3)
                    break # Only 1 news per run - keep your speed
        except Exception as e:
            print(f"NEWS LOOP ERROR {e}")

    save_state(state)
    print(f"DONE POSTED {posted} - SUCCESS - Will save history now")

if __name__=="__main__":
    try:
        main()
    except Exception as e:
        print(f"CRITICAL ERROR BUT EXIT 0 so history saves: {e}")
        # Force save empty state to not lose file
        try:
            if not os.path.exists(STATE_FILE):
                with open(STATE_FILE,"w") as f: json.dump({"kickoff":[],"goals":[],"red":[],"ft":[],"news":[]}, f)
        except: pass
