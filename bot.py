# bot.py - V21 FULL FIX GOALS + RED + FT + LINEUPS + NEWS 🟢
import os, json, requests, random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

PAGE_ID = os.getenv("PAGE_ID", "").strip()
PAGE_TOKEN = os.getenv("PAGE_ACCESS_TOKEN", "").strip()
STATE_FILE = "posted_state.json"

LEAGUES = {
    "eng.1": "Premier League",
    "esp.1": "La Liga",
    "ger.1": "Bundesliga",
    "ita.1": "Serie A",
    "fra.1": "Ligue 1",
    "ned.1": "Eredivisie",
    "ken.1": "KPL Kenya",
    "nga.1": "NPFL Nigeria",
    "rsa.1": "PSL South Africa",
    "uefa.champions": "Champions League",
    "uefa.europa": "Europa League",
    "uefa.europa.conf": "Conference League",
}

ESPN_SCORE = "https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard"
ESPN_SUMMARY = "https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/summary?event={event_id}"
ESPN_NEWS = "https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/news"
EAT = ZoneInfo("Africa/Nairobi")

def load_state():
    try:
        with open(STATE_FILE) as f:
            s = json.load(f)
            s.setdefault("lineups", {}); s.setdefault("kickoff", {}); s.setdefault("ht", {}); s.setdefault("ft", {})
            s.setdefault("red", {}); s.setdefault("goals", {}); s.setdefault("cards", {}); s.setdefault("daily_date", "")
            s.setdefault("news_ids", {}); s.setdefault("last_news", "")
            return s
    except:
        return {"lineups": {}, "kickoff": {}, "ht": {}, "ft": {}, "red": {}, "goals": {}, "cards": {}, "daily_date": "", "news_ids": {}, "last_news": ""}

def save_state(s):
    with open(STATE_FILE, "w") as f:
        json.dump(s, f, indent=2)

def fb_post(msg):
    if not PAGE_ID or not PAGE_TOKEN:
        print("ERROR Secrets empty")
        return None
    url = f"https://graph.facebook.com/v20.0/{PAGE_ID}/feed"
    try:
        r = requests.post(url, data={"message": msg, "access_token": PAGE_TOKEN}, timeout=25)
        print(f"FB {r.status_code}: {r.text[:800]}")
        return r.json().get("id") if r.status_code == 200 else None
    except Exception as e:
        print(f"FB exception {e}")
        return None

def get_events():
    all_ev = []
    today = datetime.now(EAT).strftime("%Y%m%d")
    for code, name in LEAGUES.items():
        try:
            url = ESPN_SCORE.format(league=code) + f"?dates={today}"
            resp = requests.get(url, timeout=12)
            if resp.status_code!=200:
                resp = requests.get(ESPN_SCORE.format(league=code), timeout=12)
            data = resp.json()
            evs = data.get("events", [])
            for e in evs:
                e["_league_code"]=code; e["_league_name"]=name
            all_ev.extend(evs)
            print(f"{code} -> {len(evs)}")
        except Exception as e:
            print(f"{code} err {e}")
    return all_ev

def get_details(league_code, event_id):
    try:
        url = ESPN_SUMMARY.format(league=league_code, event_id=event_id)
        r = requests.get(url, timeout=12)
        if r.status_code==200:
            return r.json()
        # fallback to CDN API for playbyplay (better for goals/cards)
        cdn_url = f"https://cdn.espn.com/core/soccer/playbyplay?xhr=1&gameId={event_id}"
        r2 = requests.get(cdn_url, timeout=12)
        if r2.status_code==200:
            j = r2.json()
            return j.get("gamepackageJSON", j)
    except Exception as e:
        print(f"details err {e}")
    return None

def fetch_news():
    articles = []
    for league in ["eng.1","esp.1","ita.1","uefa.champions"]:
        try:
            r = requests.get(ESPN_NEWS.format(league=league), timeout=10)
            if r.status_code==200:
                data = r.json()
                arts = data.get("articles", [])
                for a in arts[:5]:
                    articles.append({
                        "id": a.get("id") or a.get("headline","")[:50],
                        "headline": a.get("headline",""),
                        "desc": a.get("description","")[:300],
                        "link": a.get("links",{}).get("web",{}).get("href","") or a.get("links",{}).get("api",{}).get("news",{}).get("href","")
                    })
        except:
            pass
    # Also BBC-style via now API
    try:
        r = requests.get("https://now.core.api.espn.com/v1/sports/news?limit=20&sport=soccer", timeout=10)
        if r.status_code==200:
            for h in r.json().get("headlines", [])[:10]:
                articles.append({"id": h.get("id",""), "headline": h.get("headline",""), "desc": h.get("description","")[:300], "link": h.get("links",{}).get("web",{}).get("href","")})
    except:
        pass
    return articles

def parse_key_events(details):
    """Robust parser for goals, red cards from multiple ESPN formats"""
    goals, reds = [], []
    try:
        # Format 1: site v2 summary -> header.competitions[0].details
        header = details.get("header", {})
        comps = header.get("competitions", [])
        if comps:
            d = comps[0]
            # details array contains goals and cards
            for ev in d.get("details", []) + d.get("scoringPlays", []):
                t = ev.get("type",{}).get("text","") if isinstance(ev.get("type"), dict) else ev.get("type","")
                if "goal" in str(t).lower() or "scoringplay" in str(ev.get("type","")).lower() or ev.get("scoringPlay"):
                    goals.append(ev)
                if "red" in str(t).lower() or "red card" in str(ev.get("text","")).lower():
                    reds.append(ev)
            # also header keyEvents
            for ev in header.get("keyEvents", []):
                if "goal" in ev.get("text","").lower(): goals.append(ev)
                if "red" in ev.get("text","").lower(): reds.append(ev)

        # Format 2: top-level details
        for ev in details.get("details", []) + details.get("keyEvents", []) + details.get("scoringPlays", []):
            txt = (ev.get("text","") + ev.get("type",{}).get("text","") if isinstance(ev.get("type"), dict) else ev.get("type","")).lower()
            if "goal" in txt: goals.append(ev)
            if "red" in txt: reds.append(ev)

        # Format 3: CDN playbyplay -> header.competitions[0].details or plays
        c = details.get("header", {}).get("competitions", [{}])[0] if isinstance(details.get("header"), dict) else {}
        for ev in c.get("details", []):
            if "goal" in ev.get("type",{}).get("text","").lower(): goals.append(ev)
            if "red" in ev.get("type",{}).get("text","").lower(): reds.append(ev)

        # Format 4: gamepackage -> keyEvents
        gp = details.get("gamepackageJSON", details)
        if isinstance(gp, dict):
            for ev in gp.get("keyEvents", []) + gp.get("header", {}).get("competitions", [{}])[0].get("details", []) if gp.get("header") else []:
                if isinstance(ev, dict):
                    if "goal" in str(ev.get("type","")).lower() or "goal" in ev.get("text","").lower(): goals.append(ev)
                    if "red" in str(ev.get("type","")).lower() or "red card" in ev.get("text","").lower(): reds.append(ev)
    except Exception as e:
        print(f"parse err {e}")
    # dedup by id/text
    uniq_g, uniq_r = [], []
    seen=set()
    for g in goals:
        gid = str(g.get("id","")) + str(g.get("clock",{}).get("value","")) + str(g.get("text",""))[:30]
        if gid not in seen:
            seen.add(gid); uniq_g.append(g)
    seen=set()
    for r in reds:
        rid = str(r.get("id","")) + str(r.get("text",""))[:30]
        if rid not in seen:
            seen.add(rid); uniq_r.append(r)
    return uniq_g, uniq_r

def main():
    state = load_state()
    now = datetime.now(EAT)
    print(f"V21 GOALS+RED+NEWS - {now} PAGE_ID {PAGE_ID}")
    events = get_events()
    posted = 0
    today_str = now.strftime("%Y-%m-%d")

    # DAILY FIXTURES
    if state.get("daily_date")!= today_str and events:
        by_league={}
        for ev in events:
            comps=ev.get("competitions",[])
            if not comps: continue
            competitors=comps[0].get("competitors",[])
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
            if fb_post(msg):
                state["daily_date"]=today_str; posted+=1

    # LIVE LOOP
    for ev in events:
        ev_id=ev.get("id"); league_code=ev["_league_code"]; comp_name=ev["_league_name"]
        comps=ev.get("competitions",[]);
        if not comps: continue
        c=comps[0]
        status_name=c.get("status",{}).get("type",{}).get("name","")
        status_detail=c.get("status",{}).get("type",{}).get("detail","")
        short_detail=c.get("status",{}).get("type",{}).get("shortDetail","")
        competitors=c.get("competitors",[])
        if len(competitors)<2: continue
        home=next((x for x in competitors if x.get("homeAway")=="home"), competitors[0])
        away=next((x for x in competitors if x.get("homeAway")=="away"), competitors[-1])
        h_team=home.get("team",{}).get("displayName","Home")
        a_team=away.get("team",{}).get("displayName","Away")
        h_score=home.get("score","0"); a_score=away.get("score","0")

        details=get_details(league_code, ev_id)
        if not details: continue

        # 1 LINEUPS - FIXED to check roster
        if ev_id not in state["lineups"]:
            lineups=details.get("lineups",[]) or details.get("header",{}).get("competitions",[{}])[0].get("lineups",[]) or details.get("roster",[])
            if lineups and len(lineups)>=2:
                msg=f"🟢 LINEUPS - {comp_name}\n\n{h_team} vs {a_team}\n{short_detail}\n\n"
                for team_line in lineups[:2]:
                    tname=team_line.get("team",{}).get("displayName","") if isinstance(team_line.get("team"), dict) else team_line.get("team","")
                    formation=team_line.get("formation","")
                    msg+=f"{tname} {formation}\n"
                    players=team_line.get("players",[]) or team_line.get("athletes",[])
                    for p in players[:11]:
                        if isinstance(p, dict):
                            aname=p.get("athlete",{}).get("displayName","") or p.get("displayName","")
                            msg+=f"- {aname}\n"
                    msg+="\n"
                msg+="Kickoff soon! 🟢\nUNFILTERED SCORES"
                if fb_post(msg):
                    state["lineups"][ev_id]=True; posted+=1

        # 2 KICKOFF - now triggers for any IN_PROGRESS if not posted
        if status_name=="STATUS_IN_PROGRESS" and ev_id not in state["kickoff"]:
            if any(x in short_detail for x in ["0'","1'","2'","3'","4'","5'"]) or "1st Half" in status_detail or "First Half" in status_detail:
                msg=f"🟢 KICK OFF! - {comp_name}\n\n{h_team} vs {a_team}\n\n⚽ Game Started!\n{status_detail}\n\nLive updates here 🟢\n#UnfilteredScores"
                if fb_post(msg):
                    state["kickoff"][ev_id]=True; posted+=1
            elif ev_id in state["lineups"] or h_score=="0" and a_score=="0":
                # fallback: if lineups posted but kickoff missed, post now once
                msg=f"🟢 KICK OFF! - {comp_name}\n\n{h_team} 0 - 0 {a_team}\n\n⚽ LIVE NOW!\nUNFILTERED SCORES 🟢"
                if fb_post(msg):
                    state["kickoff"][ev_id]=True; posted+=1

        # 3 GOALS + RED CARDS - NEW ROBUST PARSER
        g_list, r_list = parse_key_events(details)
        # GOALS
        if status_name=="STATUS_IN_PROGRESS":
            for g in g_list:
                gid = f"{ev_id}_goal_{g.get('id','')}_{g.get('clock',{}).get('value','')}_{g.get('text','')[:20]}"
                if gid not in state["goals"]:
                    scorer = g.get("athlete",{}).get("displayName","") or g.get("participants",[{}])[0].get("athlete",{}).get("displayName","") if g.get("participants") else ""
                    if not scorer:
                        scorer = g.get("text","GOAL!").split("-")[0][:40]
                    minute = g.get("clock",{}).get("displayValue","") or g.get("clock","") or ""
                    team = g.get("team",{}).get("displayName","") or ""
                    msg=f"⚽ GOAL! 🟢\n\n{comp_name}\n{h_team} {h_score} - {a_score} {a_team}\n\n⚽ {scorer} {team} {minute}'\n{g.get('text','')}\n\n🟢 LIVE"
                    if fb_post(msg):
                        state["goals"][gid]=True; posted+=1
        # RED CARDS
        for rc in r_list:
            rid = f"{ev_id}_red_{rc.get('id','')}_{rc.get('text','')[:20]}"
            if rid not in state["red"]:
                player = rc.get("athlete",{}).get("displayName","") or rc.get("text","RED CARD")[:80]
                minute = rc.get("clock",{}).get("displayValue","") or ""
                msg=f"🟥 RED CARD! 🟢\n\n{comp_name}\n{h_team} {h_score} - {a_score} {a_team}\n\n🟥 {player} {minute}'\n{rc.get('text','')}\n\nUNFILTERED SCORES 🟢"
                if fb_post(msg):
                    state["red"][rid]=True; posted+=1

        # 4 HALF TIME
        if status_name=="STATUS_HALFTIME" and ev_id not in state["ht"]:
            msg=f"⏸️ HALF TIME - {comp_name} 🟢\n\n{h_team} {h_score} - {a_score} {a_team}\n\nHT\nUNFILTERED SCORES 🟢"
            if fb_post(msg):
                state["ht"][ev_id]=True; posted+=1

        # 5 FULL TIME - IMPROVED (catches FINAL + 90' + FT detail)
        is_ft = status_name=="STATUS_FINAL" or "Full Time" in status_detail or "FT" in short_detail or "Final" in status_detail
        if is_ft and ev_id not in state["ft"]:
            try:
                hs=int(h_score); aws=int(a_score)
            except:
                hs=0; aws=0
            winner=f"{h_team} WINS!" if hs>aws else f"{a_team} WINS!" if aws>hs else "DRAW!"
            msg=f"🟢 FULL TIME - {comp_name}\n\n{h_team} {h_score} - {a_score} {a_team}\n\n{winner}\nFT | {status_detail}\nUNFILTERED SCORES 🟢"
            if fb_post(msg):
                state["ft"][ev_id]=True; posted+=1

    # 6 NEWS FILLER - So page never looks dead
    last_news_str = state.get("last_news","")
    try:
        last_news_time = datetime.fromisoformat(last_news_str) if last_news_str else now - timedelta(hours=3)
    except:
        last_news_time = now - timedelta(hours=3)

    hours_since_news = (now - last_news_time).total_seconds()/3600
    if posted==0 and hours_since_news >= 2: # if nothing live posted in 2h, post news
        news = fetch_news()
        random.shuffle(news)
        for art in news:
            nid = art["id"]
            if nid not in state["news_ids"]:
                headline = art["headline"]
                desc = art["desc"]
                if headline:
                    msg = f"📰 FOOTBALL NEWS 🟢\n\n{headline}\n\n{desc}\n\n#FootballNews #UnfilteredScores"
                    if fb_post(msg):
                        state["news_ids"][nid]=True
                        state["last_news"]=now.isoformat()
                        posted+=1
                        print(f"Posted news: {headline[:60]}")
                        break
        # keep only last 100 news ids
        if len(state["news_ids"])>100:
            state["news_ids"] = dict(list(state["news_ids"].items())[-100:])

    print(f"V21 Done Posted:{posted} Events:{len(events)}")
    save_state(state)

if __name__=="__main__":
    main()
