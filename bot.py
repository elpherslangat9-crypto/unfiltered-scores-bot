# bot.py - V20.5 FULL BRAND 🟢 UNFILTERED SCORES
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
    "ken.1": "KPL - Kenya",
    "nga.1": "NPFL - Nigeria",
    "rsa.1": "PSL - South Africa",
    "uefa.champions": "🏆 Champions League",
    "uefa.europa": "🏆 Europa League",
    "uefa.europa.conf": "🏆 Conference League",
}

ESPN_SCORE = "https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard"
ESPN_SUMMARY = "https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/summary?event={event_id}"
EAT = ZoneInfo("Africa/Nairobi")

def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except:
        return {"lineups": {}, "ht": {}, "ft": {}, "red": {}, "goals": {}, "transfers": [], "daily_date": "", "daily_posted": []}

def save_state(s):
    with open(STATE_FILE, "w") as f:
        json.dump(s, f, indent=2)

def fb_post(msg):
    print(f"DEBUG PAGE_ID: {PAGE_ID} len:{len(PAGE_ID)} token_len:{len(PAGE_TOKEN)} start:{PAGE_TOKEN[:12]}")
    if not PAGE_ID or not PAGE_TOKEN:
        print("ERROR: Secrets empty - check PAGE_ID and PAGE_ACCESS_TOKEN")
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
    print(f"V20.5 FULL BRAND 🟢 - {now} - PAGE_ID {PAGE_ID}")
    events = get_events()
    posted = 0
    today_str = now.strftime("%Y-%m-%d")

    # 1. DAILY FIXTURES - Morning Post 🟢
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
            msg = f"🟢 TODAY'S FIXTURES - {today_str}\n"
            msg += f"📅 {now.strftime('%A %d %B %Y')} | EAT\n"
            msg += f"⚽ UNFILTERED SCORES 🟢\n\n"
            total = 0
            for lname, games in by_league.items():
                msg += f"{lname} ({len(games)})\n"
                for g in games[:8]:
                    msg += f"• {g}\n"
                msg += "\n"
                total += len(games)
            msg += f"Total: {total} matches 🟢\n#UnfilteredScores #LiveScores"
            if fb_post(msg):
                state["daily_date"] = today_str
                posted += 1

    # 2. LIVE EVENTS PROCESSING
    for ev in events:
        ev_id = ev.get("id")
        league_code = ev["_league_code"]
        comp_name = ev["_league_name"]
        comps = ev.get("competitions", [])
        if not comps: continue
        c = comps[0]
        status_name = c.get("status", {}).get("type", {}).get("name", "")
        status_detail = c.get("status", {}).get("type", {}).get("detail", "")
        competitors = c.get("competitors", [])
        if len(competitors) < 2: continue
        home = next((x for x in competitors if x.get("homeAway") == "home"), competitors[0])
        away = next((x for x in competitors if x.get("homeAway") == "away"), competitors[-1])
        h_team = home.get("team", {}).get("displayName", "Home")
        a_team = away.get("team", {}).get("displayName", "Away")
        h_score = home.get("score", "0")
        a_score = away.get("score", "0")
        h_id = home.get("team", {}).get("id")
        a_id = away.get("team", {}).get("id")

        details = None
        if status_name in ["STATUS_IN_PROGRESS", "STATUS_HALFTIME", "STATUS_END_PERIOD", "STATUS_FINAL"]:
            details = get_details(league_code, ev_id)

        # LINEUPS - 1 Hour before
        if status_name == "STATUS_SCHEDULED" and ev_id not in state["lineups"]:
            if details:
                lineups = details.get("lineups", []) or details.get("roster", [])
                if lineups:
                    msg = f"🟢 LINEUPS - {comp_name}\n\n"
                    msg += f"{h_team} vs {a_team}\n"
                    msg += f"⏰ {status_detail}\n\n"
                    # Try extract formations
                    try:
                        for team_line in details.get("lineups", []):
                            tname = team_line.get("team", {}).get("displayName", "")
                            formation = team_line.get("formation", "")
                            msg += f"{tname} {formation}\n"
                            for p in team_line.get("players", [])[:11]:
                                msg += f"• {p.get('athlete', {}).get('displayName','')}\n"
                            msg += "\n"
                    except:
                        msg += "Lineups are out! Check comments 🟢\n"
                    msg += f"\n#UnfilteredScores 🟢"
                    if fb_post(msg):
                        state["lineups"][ev_id] = True
                        posted += 1

        # GOAL ALERT
        if details:
            try:
                # Track goals via scoring plays
                scoring_plays = details.get("header", {}).get("competitions", [{}])[0].get("scoringPlays", []) or details.get("scoringPlays", [])
                for play in scoring_plays:
                    play_id = play.get("id", "") + ev_id
                    if play_id not in state["goals"]:
                        scorer = play.get("athlete", {}).get("displayName", "Goal")
                        minute = play.get("clock", {}).get("displayValue", "") or play.get("type", {}).get("text", "")
                        team = play.get("team", {}).get("displayName", "")
                        msg = f"⚽ GOAL ALERT! 🟢\n\n"
                        msg += f"{comp_name}\n"
                        msg += f"{h_team} {h_score} - {a_score} {a_team}\n\n"
                        msg += f"⚽ {scorer} ({team}) {minute}'\n\n"
                        msg += f"🟢 LIVE 🟢 #UnfilteredScores"
                        if fb_post(msg):
                            state["goals"][play_id] = True
                            posted += 1
            except Exception as e:
                print(f"goal err {e}")

        # RED CARD
        if details and ev_id not in state["red"]:
            try:
                # Check for red cards in stats
                if "red" in json.dumps(details).lower():
                    # Simple detection
                    msg = f"🟥 RED CARD! 🟢\n\n{comp_name}\n{h_team} {h_score} - {a_score} {a_team}\n\n🟥 Someone sent off!\n{status_detail}\n\n#UnfilteredScores 🟢"
                    # Avoid spam - only if in progress
                    if status_name == "STATUS_IN_PROGRESS":
                        # Check actual red card in details to prevent false
                        pass
            except:
                pass

        # HALF TIME
        if status_name in ["STATUS_HALFTIME", "STATUS_END_PERIOD"] and ev_id not in state["ht"]:
            if "halftime" in status_detail.lower() or status_name == "STATUS_HALFTIME":
                msg = f"⏸️ HALF TIME - {comp_name} 🟢\n\n"
                msg += f"{h_team} {h_score} - {a_score} {a_team}\n\n"
                msg += f"⏸️ HT | {status_detail}\n\n🟢 UNFILTERED SCORES"
                if fb_post(msg):
                    state["ht"][ev_id] = True
                    posted += 1

        # FULL TIME
        if status_name == "STATUS_FINAL" and ev_id not in state["ft"]:
            msg = f"🟢 FULL TIME - {comp_name}\n\n"
            msg += f"{h_team} {h_score} - {a_score} {a_team}\n\n"
            winner = ""
            if h_score > a_score:
                winner = f"✅ {h_team} WIN!"
            elif a_score > h_score:
                winner = f"✅ {a_team} WIN!"
            else:
                winner = f"🤝 DRAW!"
            msg += f"{winner}\n\n"
            msg += f"✅ FT | {status_detail}\n"
            msg += f"🟢 UNFILTERED SCORES | #FT"
            if fb_post(msg):
                state["ft"][ev_id] = True
                posted += 1

    print(f"V20.5 FULL BRAND Done - Posted:{posted} Events:{len(events)}")
    save_state(state)

if __name__ == "__main__":
    main()
