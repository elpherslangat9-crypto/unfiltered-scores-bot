# bot.py - V20.6 FIX KICKOFF + LINEUPS 🟢
import os, json, requests
from datetime import datetime
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
EAT = ZoneInfo("Africa/Nairobi")

def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except:
        return {"lineups": {}, "kickoff": {}, "ht": {}, "ft": {}, "red": {}, "goals": {}, "daily_date": ""}

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
        print(f"FB {r.status_code}: {r.text[:1200]}")
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
            if resp.status_code!= 200:
                resp = requests.get(ESPN_SCORE.format(league=code), timeout=12)
            data = resp.json()
            evs = data.get("events", [])
            for e in evs:
                e["_league_code"] = code
                e["_league_name"] = name
            all_ev.extend(evs)
            print(f"{code} -> {len(evs)}")
        except Exception as e:
            print(f"{code} err {e}")
    return all_ev

def get_details(league_code, event_id):
    try:
        url = ESPN_SUMMARY.format(league=league_code, event_id=event_id)
        r = requests.get(url, timeout=12)
        return r.json() if r.status_code == 200 else None
    except:
        return None

def main():
    state = load_state()
    now = datetime.now(EAT)
    print(f"V20.6 KICKOFF FIX - {now} PAGE_ID {PAGE_ID}")
    events = get_events()
    posted = 0
    today_str = now.strftime("%Y-%m-%d")

    # DAILY FIXTURES
    if state.get("daily_date")!= today_str and events:
        by_league = {}
        for ev in events:
            comps = ev.get("competitions", [])
            if not comps: continue
            competitors = comps[0].get("competitors", [])
            if len(competitors) < 2: continue
            home = next((x for x in competitors if x.get("homeAway") == "home"), competitors[0])
            away = next((x for x in competitors if x.get("homeAway") == "away"), competitors[-1])
            h = home.get("team", {}).get("displayName", "")
            a = away.get("team", {}).get("displayName", "")
            time_str = comps[0].get("status", {}).get("type", {}).get("shortDetail", "")
            by_league.setdefault(ev["_league_name"], []).append(f"{h} vs {a} - {time_str}")
        if by_league:
            msg = f"🟢 TODAY'S FIXTURES - {today_str}\n{now.strftime('%A %d %B')} | EAT\nUNFILTERED SCORES 🟢\n\n"
            total=0
            for lname, games in by_league.items():
                msg += f"{lname} ({len(games)})\n"
                for g in games[:8]: msg += f"- {g}\n"
                msg += "\n"
                total+=len(games)
            msg += f"Total: {total} matches 🟢\n#UnfilteredScores"
            if fb_post(msg):
                state["daily_date"]=today_str
                posted+=1

    # LIVE LOOP - NOW FETCH DETAILS FOR ALL
    for ev in events:
        ev_id = ev.get("id")
        league_code = ev["_league_code"]
        comp_name = ev["_league_name"]
        comps = ev.get("competitions", [])
        if not comps: continue
        c = comps[0]
        status_name = c.get("status", {}).get("type", {}).get("name", "")
        status_detail = c.get("status", {}).get("type", {}).get("detail", "")
        short_detail = c.get("status", {}).get("type", {}).get("shortDetail", "")
        competitors = c.get("competitors", [])
        if len(competitors) < 2: continue
        home = next((x for x in competitors if x.get("homeAway") == "home"), competitors[0])
        away = next((x for x in competitors if x.get("homeAway") == "away"), competitors[-1])
        h_team = home.get("team", {}).get("displayName", "Home")
        a_team = away.get("team", {}).get("displayName", "Away")
        h_score = home.get("score", "0")
        a_score = away.get("score", "0")

        # FIX: ALWAYS fetch details for SCHEDULED too (for lineups)
        details = get_details(league_code, ev_id)

        # 1 LINEUPS - Now works!
        if ev_id not in state["lineups"] and details:
            lineups = details.get("lineups", [])
            if lineups and len(lineups)>=2:
                msg = f"🟢 LINEUPS - {comp_name}\n\n{h_team} vs {a_team}\n{short_detail}\n\n"
                for team_line in lineups[:2]:
                    tname = team_line.get("team", {}).get("displayName", "")
                    formation = team_line.get("formation", "")
                    msg += f"{tname} {formation}\n"
                    for p in team_line.get("players", [])[:11]:
                        aname = p.get("athlete", {}).get("displayName", "")
                        pos = p.get("position", {}).get("displayName", "")
                        msg += f"- {aname} {f'({pos})' if pos else ''}\n"
                    msg += "\n"
                msg += "Kickoff soon! 🟢\nUNFILTERED SCORES"
                if fb_post(msg):
                    state["lineups"][ev_id]=True
                    posted+=1

        # 2 KICKOFF - NEW!
        if status_name == "STATUS_IN_PROGRESS" and ev_id not in state["kickoff"]:
            # If match just started (score 0-0 and early minutes)
            if "1'" in short_detail or "2'" in short_detail or "0'" in short_detail or "First Half" in status_detail:
                msg = f"🟢 KICK OFF! - {comp_name}\n\n{h_team} vs {a_team}\n\n⚽ Game Started!\n{status_detail}\n\nLive updates here 🟢\n#UnfilteredScores"
                if fb_post(msg):
                    state["kickoff"][ev_id]=True
                    posted+=1
            elif ev_id not in state["kickoff"] and ev_id in state["lineups"]:
                # Fallback: if we had lineups, post kickoff even if minute missing
                msg = f"🟢 KICK OFF! - {comp_name}\n\n{h_team} 0 - 0 {a_team}\n\n⚽ LIVE NOW!\nUNFILTERED SCORES 🟢"
                if fb_post(msg):
                    state["kickoff"][ev_id]=True
                    posted+=1

        # 3 GOAL
        if details and status_name == "STATUS_IN_PROGRESS":
            try:
                comp_data = details.get("header", {}).get("competitions", [{}])[0]
                plays = comp_data.get("scoringPlays", []) or details.get("scoringPlays", [])
                for play in plays:
                    pid = f"{ev_id}_{play.get('id','')}"
                    if pid not in state["goals"]:
                        scorer = play.get("athlete", {}).get("displayName", "GOAL")
                        minute = play.get("clock", {}).get("displayValue", "")
                        team = play.get("team", {}).get("displayName", "")
                        msg = f"⚽ GOAL! 🟢\n\n{comp_name}\n{h_team} {h_score} - {a_score} {a_team}\n\n⚽ {scorer} ({team}) {minute}'\n\n🟢 LIVE"
                        if fb_post(msg):
                            state["goals"][pid]=True
                            posted+=1
            except Exception as e:
                print(f"goal err {e}")

        # 4 HALF TIME
        if status_name == "STATUS_HALFTIME" and ev_id not in state["ht"]:
            msg = f"⏸️ HALF TIME - {comp_name} 🟢\n\n{h_team} {h_score} - {a_score} {a_team}\n\nHT\nUNFILTERED SCORES 🟢"
            if fb_post(msg):
                state["ht"][ev_id]=True
                posted+=1

        # 5 FULL TIME
        if status_name == "STATUS_FINAL" and ev_id not in state["ft"]:
            winner = f"{h_team} WINS!" if h_score > a_score else f"{a_team} WINS!" if a_score > h_score else "DRAW!"
            msg = f"🟢 FULL TIME - {comp_name}\n\n{h_team} {h_score} - {a_score} {a_team}\n\n{winner}\nFT | {status_detail}\nUNFILTERED SCORES 🟢"
            if fb_post(msg):
                state["ft"][ev_id]=True
                posted+=1

    print(f"V20.6 Done Posted:{posted} Events:{len(events)}")
    save_state(state)

if __name__ == "__main__":
    main()
