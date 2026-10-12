# bot.py V23 FINAL - NO REPEAT, NO MISSED GAME 🟢
import os, json, requests, re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

PAGE_ID = os.getenv("PAGE_ID")
PAGE_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
STATE_FILE = "posted_state.json"

LEAGUES = {
    "eng.1": "Premier League", "esp.1": "La Liga", "ger.1": "Bundesliga",
    "ita.1": "Serie A", "fra.1": "Ligue 1", "ned.1": "Eredivisie",
    "ken.1": "KPL Kenya", "nga.1": "NPFL", "uefa.champions": "UCL",
    "uefa.europa": "UEL", "uefa.europa.conf": "Conference",
}

EAT = ZoneInfo("Africa/Nairobi")
SCORE_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/scoreboard"
SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/summary?event={eid}"

def load_state():
    try:
        with open(STATE_FILE) as f:
            s = json.load(f)
            # ensure keys
            for k in ["kickoff","lineup","goals","red","ht","ft","live30","live60","postponed","news"]:
                s.setdefault(k, {} if k!="news" else [])
            return s
    except:
        return {"kickoff":{}, "lineup":{}, "goals":{}, "red":{}, "ht":{}, "ft":{}, "live30":{}, "live60":{}, "postponed":{}, "news":[]}

def save_state(s):
    # keep small
    for k in ["kickoff","lineup","goals","red","ht","ft","live30","live60","postponed"]:
        if isinstance(s.get(k), dict) and len(s[k]) > 400:
            s[k] = dict(list(s[k].items())[-250:])
    if len(s.get("news",[])) > 80: s["news"] = s["news"][-40:]
    with open(STATE_FILE,"w") as f: json.dump(s,f)

def post(msg):
    if not PAGE_ID or not PAGE_TOKEN:
        print("NO TOKEN"); return False
    try:
        r = requests.post(f"https://graph.facebook.com/v20.0/{PAGE_ID}/feed",
                          data={"message": msg, "access_token": PAGE_TOKEN}, timeout=15)
        print(f"POST {r.status_code}: {msg[:80]}")
        return r.status_code == 200
    except Exception as e:
        print(f"post err {e}"); return False

def get_all_events():
    events = []
    # Check yesterday, today, tomorrow so we NEVER miss late KPL or early UCL
    dates = [
        (datetime.now(EAT) - timedelta(days=1)).strftime("%Y%m%d"),
        datetime.now(EAT).strftime("%Y%m%d"),
        (datetime.now(EAT) + timedelta(days=1)).strftime("%Y%m%d"),
    ]
    for lg, lname in LEAGUES.items():
        for d in dates:
            try:
                url = SCORE_URL.format(lg=lg) + f"?dates={d}"
                data = requests.get(url, timeout=8).json()
                for ev in data.get("events",[]):
                    ev["_lname"] = lname
                    ev["_code"] = lg
                    ev["_date"] = d
                    events.append(ev)
                # if we got events for today, no need to check other dates for same league
                if d == dates[1] and data.get("events"): break
            except: pass
    # deduplicate by id
    uniq = {}
    for ev in events: uniq[ev["id"]] = ev
    return list(uniq.values())

def main():
    state = load_state()
    now = datetime.now(EAT)
    events = get_all_events()
    print(f"V23 - {now} - Events:{len(events)}")
    posted = 0

    for ev in events:
        ev_id = ev["id"]
        comp = ev["competitions"][0]
        status_name = comp["status"]["type"]["name"]
        short = comp["status"]["type"].get("shortDetail","")
        detail = comp["status"]["type"].get("detail","")
        comps = comp["competitors"]
        try:
            home = next(x for x in comps if x["homeAway"]=="home")
            away = next(x for x in comps if x["homeAway"]=="away")
        except: continue
        h_name = home["team"]["displayName"]; a_name = away["team"]["displayName"]
        h_score = home.get("score","0"); a_score = away.get("score","0")
        lg = ev["_lname"]; lg_code = ev["_code"]

        # --- POSTPONED / CANCELLED - IMPORTANT ---
        if "Postponed" in detail or "Canceled" in detail or "Abandoned" in detail:
            if ev_id not in state["postponed"]:
                if post(f"⚠️ {detail.upper()} 🟢\n\n{lg}\n{h_name} vs {a_name}\n\n{detail}\n#UnfilteredScores"):
                    state["postponed"][ev_id]=1; posted+=1

        # Skip if not live and not final and not about to start
        if status_name not in ["STATUS_IN_PROGRESS","STATUS_HALFTIME","STATUS_FINAL","STATUS_SCHEDULED","STATUS_END"]:
            continue

        # Fetch details ONLY if live / HT / FT
        details_list, lineups = [], []
        if status_name in ["STATUS_IN_PROGRESS","STATUS_HALFTIME","STATUS_FINAL","STATUS_END"]:
            try:
                det = requests.get(SUMMARY_URL.format(lg=lg_code, eid=ev_id), timeout=8).json()
                header = det.get("header",{}).get("competitions",[{}])[0]
                details_list = header.get("details", [])
                lineups = det.get("lineups", [])
            except: pass

        minute = 0
        m = re.search(r"(\d+)'", short)
        if m: minute = int(m.group(1))

        # 1. KICK OFF - 0-10 only
        if status_name == "STATUS_IN_PROGRESS" and minute <= 10 and ev_id not in state["kickoff"]:
            if post(f"🟢 KICK OFF - {lg}\n\n{h_name} vs {a_name}\n\n⚽ Game Started!\n{short}\n\nLIVE Updates Here 🟢"):
                state["kickoff"][ev_id]=1; posted+=1

        # 2. LINEUP - once, before or at kickoff
        if lineups and ev_id not in state["lineup"]:
            try:
                txt = f"📋 LINE UP - {lg} 🟢\n\n{h_name} vs {a_name}\n"
                for lineup in lineups[:2]:
                    tn = lineup.get("team",{}).get("displayName","")
                    starters = lineup.get("athletes",[]) or lineup.get("starters",[]) or []
                    txt += f"\n{tn}:\n"
                    for ath in starters[:11]:
                        name = ath.get("athlete",{}).get("displayName","") or ath.get("displayName","")
                        if name: txt += f"- {name}\n"
                txt += "\n#UnfilteredScores"
                if post(txt):
                    state["lineup"][ev_id]=1; posted+=1
            except: pass

        # 3. GOALS - NEVER REPEAT, NEVER MISS
        if status_name in ["STATUS_IN_PROGRESS","STATUS_HALFTIME"]:
            for d in details_list:
                dtype = d.get("type",{}).get("text","") if isinstance(d.get("type"),dict) else str(d.get("type",""))
                dtype = dtype.lower()
                txt = d.get("text","")
                clock = d.get("clock",{}).get("displayValue","") or str(d.get("clock",""))
                ath_id = d.get("athlete",{}).get("id","") or ""
                # STRONG ID - will never repeat
                gid = f"{ev_id}_G_{clock}_{ath_id}_{txt[:30]}"

                if "goal" in dtype and gid not in state["goals"]:
                    # IMPORTANT TAGS
                    tag = ""
                    if "penalty" in txt.lower(): tag = "(P)"
                    if "own goal" in txt.lower(): tag = "(OG)"
                    # Extract score at moment if available
                    msg = f"⚽ GOAL! {clock}' {tag} 🟢\n\n{lg}\n{h_name} {h_score} - {a_score} {a_name}\n\n⚽ {txt}\n\nLIVE 🟢"
                    if post(msg):
                        state["goals"][gid]=1; posted+=1

                if "red card" in dtype:
                    rid = f"{ev_id}_R_{clock}_{ath_id}"
                    if rid not in state["red"]:
                        if post(f"🟥 RED CARD {clock}' 🟢\n\n{lg}\n{h_name} {h_score} - {a_score} {a_name}\n\n🟥 {txt}"):
                            state["red"][rid]=1; posted+=1

            # 0-0 reminder so page not boring
            if h_score=="0" and a_score=="0":
                if 25 <= minute <= 35 and ev_id not in state["live30"]:
                    if post(f"⏱️ {minute}' LIVE - {lg} 🟢\n\n{h_name} {h_score} - {a_score} {a_name}\n\nStill 0-0, tight game!\n#UnfilteredScores"):
                        state["live30"][ev_id]=1; posted+=1
                if 60 <= minute <= 70 and ev_id not in state["live60"]:
                    if post(f"⏱️ {minute}' LIVE - {lg} 🟢\n\n{h_name} {h_score} - {a_score} {a_name}\n\nStill {h_score}-{a_score} at {minute}'\n#UnfilteredScores"):
                        state["live60"][ev_id]=1; posted+=1

        # 4. HT
        if status_name == "STATUS_HALFTIME" and ev_id not in state["ht"]:
            if post(f"⏸️ HALF TIME - {lg} 🟢\n\n{h_name} {h_score} - {a_score} {a_name}\n\nHT\n#UnfilteredScores"):
                state["ht"][ev_id]=1; posted+=1

        # 5. FT - NEVER MISS
        if status_name in ["STATUS_FINAL","STATUS_END"] and ev_id not in state["ft"]:
            if h_score!= "0" or a_score!= "0" or minute >= 80: # avoid posting 0-0 postponed as FT
                winner = f"{h_name} WINS! 🎉" if int(h_score or 0) > int(a_score or 0) else f"{a_name} WINS! 🎉" if int(a_score or 0) > int(h_score or 0) else "DRAW!"
                if post(f"✅ FULL TIME - {lg} 🟢\n\n{h_name} {h_score} - {a_score} {a_name}\n\n{winner}\nFT\n#UnfilteredScores"):
                    state["ft"][ev_id]=1; posted+=1

    # 6. NEWS - 1 per run max, so page not boring but not spam
    if posted < 2:
        try:
            for code in ["eng.1","esp.1","ken.1"]:
                data = requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/news", timeout=8).json()
                for art in data.get("articles",[])[:3]:
                    aid = str(art.get("id","") or art.get("headline","")[:30])
                    if aid in state["news"]: continue
                    title = art.get("headline","")
                    desc = art.get("description","")[:180]
                    if post(f"📰 NEWS 🟢\n\n{title}\n\n{desc}\n\n#UnfilteredScores"):
                        state["news"].append(aid); posted+=1; break
                if posted>0: break
        except: pass

    print(f"V23 DONE Posted:{posted}")
    save_state(state)

if __name__ == "__main__": main()
