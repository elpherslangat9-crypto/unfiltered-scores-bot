# bot.py - V20.2 - 12 Leagues + Daily 8AM Fixtures 🟢

import os, json, time, requests
from datetime import datetime
from zoneinfo import ZoneInfo

PAGE_ID = os.getenv("PAGE_ID", "").strip()
PAGE_TOKEN = os.getenv("PAGE_ACCESS_TOKEN", "").strip()
STATE_FILE = "posted_state.json"

LEAGUES = {
    "eng.1": "🏴󐁧󐁢󐁥󐁮󐁧󐁿 Premier League",
    "esp.1": "🇪🇸 La Liga",
    "ger.1": "🇩🇪 Bundesliga",
    "ita.1": "🇮🇹 Serie A",
    "fra.1": "🇫🇷 Ligue 1",
    "ned.1": "🇳🇱 Eredivisie",
    "ken.1": "🇰🇪 KPL - Kenya",
    "nga.1": "🇳🇬 NPFL - Nigeria",
    "rsa.1": "🇿🇦 PSL - South Africa",
    "uefa.champions": "🏆 Champions League",
    "uefa.europa": "🏆 Europa League",
    "uefa.europa.conf": "🏆 Conference League",
}

ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard"
ESPN_NEWS = "https://site.api.espn.com/apis/site/v2/sports/soccer/news"
EAT = ZoneInfo("Africa/Nairobi")

def load_state():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except:
        return {"lineups": {}, "ht": {}, "ft": {}, "red": {}, "goals": {}, "transfers": [], "daily_date": ""}

def save_state(s):
    with open(STATE_FILE, "w") as f:
        json.dump(s, f)

def fb_post(message):
    url = f"https://graph.facebook.com/v19.0/{PAGE_ID}/feed"
    r = requests.post(url, data={"message": message, "access_token": PAGE_TOKEN}, timeout=25)
    print(f"FB {r.status_code}: {r.text[:500]}")
    return r.json().get("id") if r.status_code == 200 else None

def get_all_events():
    all_ev = []
    today = datetime.now(EAT).strftime("%Y%m%d")
    for code, name in LEAGUES.items():
        try:
            url = ESPN_SCOREBOARD.format(league=code) + f"?dates={today}"
            resp = requests.get(url, timeout=12)
            if resp.status_code!= 200:
                resp = requests.get(ESPN_SCOREBOARD.format(league=code), timeout=12)
            data = resp.json()
            evs = data.get("events", [])
            for e in evs:
                e["_league_code"] = code
                e["_league_name"] = name
            all_ev.extend(evs)
        except Exception as e:
            print(f"{code} err {e}")
    return all_ev

def main():
    state = load_state()
    now = datetime.now(EAT)
    print(f"V20.2 - {now.strftime('%Y-%m-%d %H:%M')} EAT Leagues:{len(LEAGUES)}")
    events = get_all_events()
    posted = 0

    # --- DAILY FIXTURES AT 8AM EAT (once per day) ---
    today_str = now.strftime("%Y-%m-%d")
    hour = now.hour
    # Post if hour is 5-10 UTC which is 8-13 EAT, and not posted today
    if state.get("daily_date")!= today_str and 5 <= now.astimezone(timezone.utc).hour <= 13 or True: # always try first run
        if state.get("daily_date")!= today_str and len(events) > 0:
            # Build fixtures list grouped by league
            by_league = {}
            for ev in events:
                lname = ev["_league_name"]
                comps = ev.get("competitions", [])
                if not comps: continue
                c = comps[0]
                competitors = c.get("competitors", [])
                if len(competitors) < 2: continue
                home = next((x for x in competitors if x.get("homeAway")=="home"), competitors[0])
                away = next((x for x in competitors if x.get("homeAway")=="away"), competitors[-1])
                h = home.get("team",{}).get("displayName","")
                a = away.get("team",{}).get("displayName","")
                time_str = c.get("status",{}).get("type",{}).get("detail","")[:12]
                by_league.setdefault(lname, []).append(f"{h} vs {a} ({time_str})")

            if by_league:
                msg = f"🟢 TODAY'S FIXTURES - {today_str}\n📅 {now.strftime('%A %d %B')}\n\n"
                for lname, games in by_league.items():
                    msg += f"{lname} ({len(games)})\n"
                    for g in games[:6]:
                        msg += f"• {g}\n"
                    msg += "\n"
                msg += f"Total: {len(events)} matches in 12 Leagues 🟢\n#Fixtures #LiveScores"
                if fb_post(msg):
                    state["daily_date"] = today_str
                    posted+=1
                    time.sleep(3)

    for ev in events:
        ev_id = ev.get("id")
        comp = ev["_league_name"]
        comps = ev.get("competitions", [])
        if not comps: continue
        c = comps[0]
        status = c.get("status", {}).get("type", {})
        s_name = status.get("name", "")
        detail = status.get("detail", "")

        competitors = c.get("competitors", [])
        if len(competitors) < 2: continue
        home = next((x for x in competitors if x.get("homeAway")=="home"), competitors[0])
        away = next((x for x in competitors if x.get("homeAway")=="away"), competitors[-1])
        h_team = home.get("team", {}).get("displayName","Home")
        a_team = away.get("team", {}).get("displayName","Away")
        h_score = home.get("score","0")
        a_score = away.get("score","0")
        details = c.get("details", [])

        if s_name == "STATUS_SCHEDULED":
            if any(x.get("lineup") for x in competitors) and ev_id not in state["lineups"]:
                h_xi = [p.get("athlete",{}).get("displayName","") for p in (home.get("lineup") or [])[:11]]
                a_xi = [p.get("athlete",{}).get("displayName","") for p in (away.get("lineup") or [])[:11]]
                msg = f"🟢 STARTING XI - {comp}\n\n{h_team} vs {a_team}\n"
                if h_xi: msg += f"\n{h_team}: {', '.join(h_xi)}\n"
                if a_xi: msg += f"\n{a_team}: {', '.join(a_xi)}\n"
                msg += f"\n#Lineup 🟢"
                if fb_post(msg):
                    state["lineups"][ev_id]=True
                    posted+=1
                    time.sleep(3)

        if s_name == "STATUS_IN_PROGRESS":
            for d in details:
                txt = d.get("type",{}).get("text","")
                is_goal = "Goal" in txt or d.get("scoringPlay", False)
                is_red = "Red Card" in txt
                if is_goal:
                    key = f"g_{ev_id}_{d.get('id')}"
                    if key not in state["goals"]:
                        scorer = d.get("athletesInvolved", [{}])[0].get("displayName","")
                        clock = d.get("clock",{}).get("displayValue","")
                        msg = f"🟢 GOAL! {clock}'\n\n{comp}\n{h_team} {h_score} - {a_score} {a_team}\n\n⚽ {scorer}\n\n#LIVE 🟢"
                        if fb_post(msg):
                            state["goals"][key]=True
                            posted+=1
                            time.sleep(3)
                if is_red:
                    key = f"r_{ev_id}_{d.get('id')}"
                    if key not in state["red"]:
                        pl = d.get("athletesInvolved", [{}])[0].get("displayName","")
                        clock = d.get("clock",{}).get("displayValue","")
                        msg = f"🟢 RED CARD 🟥 {clock}'\n\n{comp}\n{h_team} {h_score} - {a_score} {a_team}\n\n{pl} sent off!\n\n#RedCard 🟢"
                        if fb_post(msg):
                            state["red"][key]=True
                            posted+=1
                            time.sleep(3)

        if "HALFTIME" in s_name.upper() or "Halftime" in detail:
            if ev_id not in state["ht"]:
                msg = f"🟢 HALF TIME - {comp}\n\n{h_team} {h_score} - {a_score} {a_team}\n\n#HT 🟢"
                if fb_post(msg):
                    state["ht"][ev_id]=True
                    posted+=1
                    time.sleep(2)
        if s_name == "STATUS_FINAL":
            if ev_id not in state["ft"]:
                msg = f"🟢 FULL TIME - {comp}\n\n{h_team} {h_score} - {a_score} {a_team}\n\n✅ FT\n\n#FT 🟢"
                if fb_post(msg):
                    state["ft"][ev_id]=True
                    posted+=1
                    time.sleep(2)

    try:
        news = requests.get(ESPN_NEWS+"?limit=25", timeout=12).json().get("articles", [])
        for art in news:
            title = art.get("headline","")
            if not title: continue
            low = title.lower()
            if any(k in low for k in ["transfer","here we go","official","agreement","joins","signs","breaking"]):
                if title not in state["transfers"]:
                    desc = (art.get("description","") or "")[:180]
                    msg = f"🟢 BREAKING: {title}\n\n{desc}\n\n#Transfers 🟢"
                    if fb_post(msg):
                        state["transfers"].append(title)
                        state["transfers"] = state["transfers"][-80:]
                        posted+=1
                        time.sleep(3)
            if posted>=8: break
    except Exception as e:
        print(f"news err {e}")

    from datetime import timezone
    print(f"V20.2 Done - Posted:{posted} Events:{len(events)}")
    save_state(state)

if __name__ == "__main__":
    from datetime import timezone
    main()
