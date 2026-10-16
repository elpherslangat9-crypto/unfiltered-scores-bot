import os, json, time, random, requests, re, xml.etree.ElementTree as ET
from datetime import datetime

FB_PAGE_ID = os.getenv("FB_PAGE_ID","").strip()
FB_TOKEN = os.getenv("FB_PAGE_TOKEN","").strip()
STATE_FILE = "posted_state.json"
HEADERS = {"User-Agent":"Mozilla/5.0","Accept":"application/json, text/html"}
MAX_PER_RUN = 2 # FAST but SAFE - 2 goals = no jail. After 1 week you can put 3
DELAY_BETWEEN = 90
SPAM_STOP = False

# YOUR BIG LEAGUES ONLY - no small leagues
ALLOWED_LEAGUES = [
    "premier league", "english premier", "epl",
    "la liga", "laliga", "spanish",
    "serie a", "italian serie",
    "bundesliga", "german bundesliga",
    "ligue 1", "french ligue",
    "eredivisie", "dutch",
    "primeira liga", "portuguese",
    "jupiler", "belgian",
    "championship", "eng.1", "eng.2",
    # EUROPE + WORLD BIG
    "uefa champions", "champions league", "ucl",
    "uefa europa", "europa league", "uel",
    "conference league", "uecl",
    "uefa super cup",
    "world cup", "world cup qual",
    "euro", "european championship",
    "africa cup", "afcon",
    "copa america",
    "nations league",
    "club world cup",
    # KENYA
    "kenya premier", "kpl", "kenyan premier", "fkf premier"
]

def load_state():
    default = {"kickoff":[],"goals":[],"red":[],"ft":[],"news":[]}
    try:
        with open(STATE_FILE,"r") as f:
            d=json.load(f)
            for k in default:
                if k not in d: d[k]=[]
                d[k]=d[k][-300:]
            return d
    except: return default

def save_state(s):
    try:
        for k in s: s[k]=s[k][-300:]
        with open(STATE_FILE,"w") as f: json.dump(s,f)
    except: pass

def is_big_league(name):
    if not name: return False
    n = name.lower()
    for allow in ALLOWED_LEAGUES:
        if allow in n:
            return True
    return False

def post_to_fb(message):
    global SPAM_STOP
    try:
        if not FB_PAGE_ID or FB_PAGE_ID=="0": return False
        url = f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}/feed"
        r = requests.post(url, data={"message":message,"access_token":FB_TOKEN}, timeout=25)
        txt=r.text
        print(f"FB {r.status_code} {txt[:500]}")
        if r.status_code==200: return True
        if "We limit" in txt or "368" in txt or "spam" in txt.lower():
            print("!!! FB JAIL DETECTED - STOPPING RUN!!!")
            SPAM_STOP=True
            return False
        return False
    except Exception as e:
        print(f"FB ERR {e}")
        return False

def get_live_espen():
    events=[]
    try:
        # FASTEST sources for big leagues
        urls = [
            "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard",
            "https://site.api.espn.com/apis/site/v2/sports/soccer/esp.1/scoreboard",
            "https://site.api.espn.com/apis/site/v2/sports/soccer/ita.1/scoreboard",
            "https://site.api.espn.com/apis/site/v2/sports/soccer/ger.1/scoreboard",
            "https://site.api.espn.com/apis/site/v2/sports/soccer/fra.1/scoreboard",
            "https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/scoreboard",
            "https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.europa/scoreboard",
            "https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.europa.conf/scoreboard",
            "https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard",
        ]
        for api_url in urls:
            try:
                data=requests.get(api_url, headers=HEADERS, timeout=12).json()
                for ev in data.get("events",[])[:15]:
                    comp=ev.get("competitions",[{}])[0]
                    if not comp: continue
                    league=comp.get("league",{}).get("name","")
                    if not is_big_league(league):
                        continue
                    st=comp.get("status",{}).get("type",{}).get("state","")
                    clock=comp.get("status",{}).get("displayClock","")
                    comps=comp.get("competitors",[])
                    if len(comps)<2: continue
                    h=comps[0]; a=comps[1]
                    hname=h.get("team",{}).get("displayName","Home")
                    aname=a.get("team",{}).get("displayName","Away")
                    hs=h.get("score","0"); as_=a.get("score","0")
                    eid=ev.get("id")

                    # GOAL - live only - 1 per match per run to be fast
                    if st=="in":
                        details=comp.get("details",[])
                        for d in details[-3:]: # last 3 details only
                            if d.get("scoringPlay"):
                                player=""
                                if d.get("athletesInvolved"): player=d["athletesInvolved"][0].get("displayName","")
                                gid=f"G_{eid}_{hs}_{as_}"
                                events.append({"id":gid,"type":"GOAL","league":league,"home":hname,"away":aname,"hs":hs,"as":as_,"minute":clock or d.get("clock",""),"player":player,"source":"ESPN"})
                                break
                    if st=="post":
                        fid=f"FT_{eid}_{hs}_{as_}"
                        events.append({"id":fid,"type":"FT","league":league,"home":hname,"away":aname,"hs":hs,"as":as_,"source":"ESPN"})
            except: continue
    except Exception as e:
        print(f"ESPN FAIL {e}")
    return events

def get_live_kpl_livescore():
    events=[]
    try:
        # Livescore free endpoint for KPL + backup
        # This works without key
        r=requests.get("https://www.livescore.com/api/v2/soccer/live", headers={"User-Agent":"Mozilla/5.0"}, timeout=12)
        if r.status_code!=200:
            # Fallback - another endpoint
            r=requests.get("https://prod-public-api.livescore.com/v1/api/app/date/soccer/20241016/0?countryCode=KE&MD=1", headers=HEADERS, timeout=12)
        data=r.json() if r.text.startswith("{") else {}
        # Try parse Stages
        stages=data.get("Stages",[]) or data.get("stages",[]) or []
        for stage in stages[:50]:
            league=stage.get("Cnm","")+" "+stage.get("Snm","")
            if not is_big_league(league):
                # Still allow if Kenya in name
                if "kenya" not in league.lower() and "kpl" not in league.lower():
                    continue
            for ev in stage.get("Events",[])[:10]:
                hname=ev.get("T1",[{}])[0].get("Nm","Home") if isinstance(ev.get("T1"),list) else ev.get("T1","")
                aname=ev.get("T2",[{}])[0].get("Nm","Away") if isinstance(ev.get("T2"),list) else ev.get("T2","")
                # Score
                tr=ev.get("Tr1","0"); tr2=ev.get("Tr2","0")
                eid=ev.get("Eid","")
                status=ev.get("Es",0) # 1=live
                if str(status)=="1" or ev.get("Eps","")=="LIVE":
                    gid=f"G_KPL_{eid}_{tr}_{tr2}"
                    events.append({"id":gid,"type":"GOAL","league":f"KPL - {league}".strip(),"home":hname,"away":aname,"hs":tr,"as":tr2,"minute":ev.get("Epr",""),"player":"","source":"LIVESCORE"})
    except Exception as e:
        print(f"KPL LIVESCORE FAIL {e}")
    return events

def get_news_all():
    news=[]
    feeds=[
        "https://feeds.bbci.co.uk/sport/football/rss.xml",
        "https://www.skysports.com/rss/12040",
        "https://www.espn.com/espn/rss/soccer/news",
        "https://www.goal.com/en/feeds/news?fmt=rss"
    ]
    football_words=["goal","premier","champions","arsenal","man utd","man city","liverpool","chelsea","barcelona","real madrid","transfer","kpl","gor mahia","afc leopards","harambee","afcon","epl","la liga","serie a"]
    for url in feeds:
        try:
            rss=requests.get(url, headers=HEADERS, timeout=10).text
            root=ET.fromstring(rss)
            for item in root.findall(".//item")[:10]:
                t=item.find("title")
                l=item.find("link")
                d=item.find("description")
                if t is None: continue
                title=t.text or ""
                # Filter football only
                low=title.lower() + (d.text.lower() if d is not None and d.text else "")
                if any(w in low for w in football_words) or "football" in low or "soccer" in low:
                    news.append({"id":(l.text if l is not None else title)[:200],"title":title.strip(),"source":"BBC/Sky/ESPN"})
        except: continue
    random.shuffle(news)
    return news[:20]

def format_msg(ev):
    # SAME FORMAT AS EARLIER - BRAND 🟢 FIRST + FOLLOWER BAIT
    if ev["type"]=="GOAL":
        return f"""🟢 GOAL ALERT! ⚽ {ev['minute']}'

{ev['home']} {ev['hs']}-{ev['as']} {ev['away']}

🎯 Scorer: {ev.get('player') or 'Live update'}
🏆 {ev['league']}
📊 {ev['source']} LIVE

Who's winning? Predict final score 👇

🔥 FOLLOW 🟢 PAGE - We post EVERY goal in 30 seconds!
#Football #LiveScore #Goal #{ev['league'].replace(' ','')[:15]} #KPL #EPL #UCL"""
    elif ev["type"]=="FT":
        return f"""🟢 FULL-TIME! 🏁

{ev['home']} {ev['hs']}-{ev['as']} {ev['away']}

🏆 {ev['league']}
📊 FT Result via {ev['source']}

Rate this match 1-10 👇 Who was MOTM?

🟢 FOLLOW for ALL big leagues + KPL LIVE - Don't miss any goal!
#FT #FullTime #LiveScore #FootballKE"""

def main():
    global SPAM_STOP
    print(f"V16 FINAL FAST BIG LEAGUES + KPL {datetime.now()}")
    state=load_state()
    all_ids=[]
    for k in state: all_ids+=state[k]

    # GET EVENTS - FAST
    evs = get_live_espen() + get_live_kpl_livescore()
    # Deduplicate by id
    uniq={}
    for e in evs:
        if e["id"] not in uniq: uniq[e["id"]]=e
    evs=list(uniq.values())
    random.shuffle(evs)
    print(f"TOTAL EVENTS {len(evs)} (filtered big leagues only)")

    posted=0
    # GOALS FIRST - fastest
    evs_sorted = sorted(evs, key=lambda x: 0 if x["type"]=="GOAL" else 1)

    for ev in evs_sorted:
        if posted>=MAX_PER_RUN or SPAM_STOP: break
        if ev["id"] in all_ids: continue
        msg=format_msg(ev)
        if post_to_fb(msg):
            if ev["type"]=="GOAL": state["goals"].append(ev["id"])
            else: state["ft"].append(ev["id"])
            posted+=1
            print(f"POSTED {ev['id']}")
            if posted<MAX_PER_RUN and not SPAM_STOP:
                time.sleep(DELAY_BETWEEN)

    # NEWS if no live goals
    if posted < MAX_PER_RUN and not SPAM_STOP:
        for n in get_news_all():
            if posted>=MAX_PER_RUN or SPAM_STOP: break
            if n["id"] in state["news"]: continue
            msg=f"""🟢 BREAKING FOOTBALL NEWS! 📰

{n['title']}

Source: {n['source']}

Your thoughts? 👇 Is this true?

🔥 FOLLOW 🟢 - 24/7 Football News + LIVE Goals + KPL!
#FootballNews #Transfer #BreakingNews #KPL #EPL"""
            if post_to_fb(msg):
                state["news"].append(n["id"])
                posted+=1
                time.sleep(DELAY_BETWEEN)

    save_state(state)
    print(f"DONE POSTED {posted}/{MAX_PER_RUN} - SUCCESS")

if __name__=="__main__":
    main()
