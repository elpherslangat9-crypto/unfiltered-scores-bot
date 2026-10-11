# bot.py - V21.1 FIX DUPLICATES + SCORE + KICKOFF 🟢
import os, json, requests, random, re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

PAGE_ID = os.getenv("PAGE_ID", "").strip()
PAGE_TOKEN = os.getenv("PAGE_ACCESS_TOKEN", "").strip()
STATE_FILE = "posted_state.json"

LEAGUES = {
    "eng.1": "Premier League", "esp.1": "La Liga", "ger.1": "Bundesliga",
    "ita.1": "Serie A", "fra.1": "Ligue 1", "ned.1": "Eredivisie",
    "ken.1": "KPL Kenya", "nga.1": "NPFL Nigeria", "rsa.1": "PSL South Africa",
    "uefa.champions": "Champions League", "uefa.europa": "Europa League", "uefa.europa.conf": "Conference League",
}

ESPN_SCORE = "https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard"
ESPN_SUMMARY = "https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/summary?event={event_id}"
ESPN_NEWS = "https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/news"
EAT = ZoneInfo("Africa/Nairobi")

def load_state():
    try:
        with open(STATE_FILE) as f:
            s=json.load(f)
            for k in ["lineups","kickoff","ht","ft","red","goals","news_ids"]:
                s.setdefault(k,{})
            s.setdefault("daily_date",""); s.setdefault("last_news","")
            return s
    except:
        return {"lineups":{}, "kickoff":{}, "ht":{}, "ft":{}, "red":{}, "goals":{}, "news_ids":{}, "daily_date":"", "last_news":""}

def save_state(s):
    with open(STATE_FILE,"w") as f: json.dump(s,f,indent=2)

def fb_post(msg):
    if not PAGE_ID or not PAGE_TOKEN: return None
    url=f"https://graph.facebook.com/v20.0/{PAGE_ID}/feed"
    try:
        r=requests.post(url, data={"message":msg,"access_token":PAGE_TOKEN}, timeout=25)
        print(f"FB {r.status_code}: {r.text[:600]}")
        return r.json().get("id") if r.status_code==200 else None
    except Exception as e:
        print(f"FB err {e}"); return None

def get_events():
    all_ev=[]; today=datetime.now(EAT).strftime("%Y%m%d")
    for code,name in LEAGUES.items():
        try:
            url=ESPN_SCORE.format(league=code)+f"?dates={today}"
            resp=requests.get(url,timeout=12)
            if resp.status_code!=200: resp=requests.get(ESPN_SCORE.format(league=code),timeout=12)
            evs=resp.json().get("events",[])
            for e in evs: e["_league_code"]=code; e["_league_name"]=name
            all_ev.extend(evs)
            print(f"{code} -> {len(evs)}")
        except Exception as e: print(f"{code} err {e}")
    return all_ev

def get_details(league_code, event_id):
    try:
        url=ESPN_SUMMARY.format(league=league_code, event_id=event_id)
        r=requests.get(url,timeout=12)
        if r.status_code==200: return r.json()
    except: pass
    return None

def parse_events(details):
    goals, reds = [], []
    try:
        header=details.get("header",{})
        comp=header.get("competitions",[{}])[0] if header.get("competitions") else {}
        # ESPN details array is most reliable
        for ev in comp.get("details",[]):
            ttype = ev.get("type",{}).get("text","").lower() if isinstance(ev.get("type"),dict) else str(ev.get("type","")).lower()
            txt = ev.get("text","").lower()
            if "goal" in ttype or "goal" in txt: goals.append(ev)
            if "red card" in ttype or "red card" in txt: reds.append(ev)
    except Exception as e: print(f"parse err {e}")
    return goals, reds

def main():
    state=load_state(); now=datetime.now(EAT)
    print(f"V21.1 FIX - {now}")
    events=get_events(); posted=0; today_str=now.strftime("%Y-%m-%d")

    # DAILY FIXTURES
    if state.get("daily_date")!=today_str and events:
        by_league={}
        for ev in events:
            comps=ev.get("competitions",[]);
            if not comps: continue
            competitors=comps[0].get("competitors",[]);
            if len(competitors)<2: continue
            home=next((x for x in competitors if x.get("homeAway")=="home"), competitors[0])
            away=next((x for x in competitors if x.get("homeAway")=="away"), competitors[-1])
            h=home.get("team",{}).get("displayName",""); a=away.get("team",{}).get("displayName","")
            time_str=comps[0].get("status",{}).get("type",{}).get("shortDetail","")
            by_league.setdefault(ev["_league_name"], []).append(f"{h} vs {a} - {time_str}")
        if by_league:
            msg=f"🟢 TODAY'S FIXTURES - {today_str}\n{now.strftime('%A %d %B')} | EAT\nUNFILTERED SCORES 🟢\n\n"
            total=0
            for lname,games in by_league.items():
                msg+=f"{lname} ({len(games)})\n"
                for g in games[:8]: msg+=f"- {g}\n"
                msg+="\n"; total+=len(games)
            msg+=f"Total: {total} matches 🟢\n#UnfilteredScores"
            if fb_post(msg): state["daily_date"]=today_str; posted+=1

    for ev in events:
        ev_id=ev.get("id"); league_code=ev["_league_code"]; comp_name=ev["_league_name"]
        comps=ev.get("competitions",[]);
        if not comps: continue
        c=comps[0]
        status_name=c.get("status",{}).get("type",{}).get("name","")
        status_detail=c.get("status",{}).get("type",{}).get("detail","")
        short_detail=c.get("status",{}).get("type",{}).get("shortDetail","")
        competitors=c.get("competitors",[]);
        if len(competitors)<2: continue
        home=next((x for x in competitors if x.get("homeAway")=="home"), competitors[0])
        away=next((x for x in competitors if x.get("homeAway")=="away"), competitors[-1])
        h_team=home.get("team",{}).get("displayName","Home"); a_team=away.get("team",{}).get("displayName","Away")
        h_score=home.get("score","0"); a_score=away.get("score","0")
        details=get_details(league_code, ev_id)
        if not details: continue

        # 1 KICKOFF - FIXED: Only first 10 minutes!
        if status_name=="STATUS_IN_PROGRESS" and ev_id not in state["kickoff"]:
            # Only if minute is 0-10 and first half
            m = re.search(r"(\d+)'", short_detail)
            minute = int(m.group(1)) if m else 999
            if minute <= 10:
                msg=f"🟢 KICK OFF! - {comp_name}\n\n{h_team} vs {a_team}\n\n⚽ Game Started!\n{status_detail}\n\nLive updates here 🟢\n#UnfilteredScores"
                if fb_post(msg): state["kickoff"][ev_id]=True; posted+=1

        # 2 GOALS + REDS
        g_list, r_list = parse_events(details)
        if status_name=="STATUS_IN_PROGRESS" or status_name=="STATUS_HALFTIME":
            for g in g_list:
                # STABLE ID: event_id + minute + player name
                clock = str(g.get("clock",{}).get("displayValue","") or g.get("clock","") or "")
                player = g.get("athlete",{}).get("displayName","") or g.get("participants",[{}])[0].get("athlete",{}).get("displayName","") if g.get("participants") else ""
                gid = f"{ev_id}_{clock}_{player}".strip()
                if not gid or len(gid)<5: gid = f"{ev_id}_{g.get('text','')[:50]}"
                if gid in state["goals"]: continue
                # Extract real score at that moment from text e.g. "FC Cologne 2, Borussia 1"
                score_match = re.search(r"(\d+),\s*.*?(\d+)", g.get("text",""))
                if score_match:
                    real_score = f"{h_team} {score_match.group(1)} - {score_match.group(2)} {a_team}"
                else:
                    real_score = f"{h_team} {h_score} - {a_score} {a_team}"
                msg=f"⚽ GOAL! 🟢\n\n{comp_name}\n{real_score}\n\n⚽ {g.get('text','')}\n\n🟢 LIVE"
                if fb_post(msg): state["goals"][gid]=True; posted+=1

            for rc in r_list:
                rid = f"{ev_id}_red_{rc.get('clock',{}).get('displayValue','')}_{rc.get('athlete',{}).get('displayName','')}"
                if rid in state["red"]: continue
                msg=f"🟥 RED CARD! 🟢\n\n{comp_name}\n{h_team} {h_score} - {a_score} {a_team}\n\n🟥 {rc.get('text','')}\n\nUNFILTERED SCORES 🟢"
                if fb_post(msg): state["red"][rid]=True; posted+=1

        if status_name=="STATUS_HALFTIME" and ev_id not in state["ht"]:
            msg=f"⏸️ HALF TIME - {comp_name} 🟢\n\n{h_team} {h_score} - {a_score} {a_team}\n\nHT\nUNFILTERED SCORES 🟢"
            if fb_post(msg): state["ht"][ev_id]=True; posted+=1

        if status_name=="STATUS_FINAL" and ev_id not in state["ft"]:
            winner=f"{h_team} WINS!" if int(h_score or 0)>int(a_score or 0) else f"{a_team} WINS!" if int(a_score or 0)>int(h_score or 0) else "DRAW!"
            msg=f"🟢 FULL TIME - {comp_name}\n\n{h_team} {h_score} - {a_score} {a_team}\n\n{winner}\nFT | {status_detail}\nUNFILTERED SCORES 🟢"
            if fb_post(msg): state["ft"][ev_id]=True; posted+=1

    print(f"V21.1 Done Posted:{posted} Events:{len(events)}")
    save_state(state)

if __name__=="__main__": main()
