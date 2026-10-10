# bot.py - V20.4 FINAL FIX - FB 200 Guaranteed
import os, json, time, requests
from datetime import datetime, timezone
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
    # DEBUG - verify secrets are loaded
    print(f"DEBUG PAGE_ID: {PAGE_ID} len:{len(PAGE_ID)} token_len:{len(PAGE_TOKEN)} start:{PAGE_TOKEN[:15]}")
    if not PAGE_ID or not PAGE_TOKEN:
        print("ERROR: PAGE_ID or PAGE_TOKEN empty! Check GitHub Secrets")
        return None
    url = f"https://graph.facebook.com/v20.0/{PAGE_ID}/feed"
    payload = {"message": message, "access_token": PAGE_TOKEN}
    try:
        r = requests.post(url, data=payload, timeout=25)
        print(f"FB {r.status_code}: {r.text[:800]}")
        if r.status_code == 200:
            return r.json().get("id")
        else:
            # Print full error for debug
            print(f"FB ERROR FULL: {r.text}")
            return None
    except Exception as e:
        print(f"FB exception {e}")
        return None

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
            print(f"{code} -> {len(evs)}")
        except Exception as e:
            print(f"{code} err {e}")
    return all_ev

def main():
    state = load_state()
    now = datetime.now(EAT)
    print(f"V20.4 FINAL - {now.strftime('%Y-%m-%d %H:%M')} EAT Leagues:{len(LEAGUES)} PAGE_ID:{PAGE_ID}")
    events = get_all_events()
    posted = 0

    today_str = now.strftime("%Y-%m-%d")
    if state.get("daily_date")!= today_str and len(events) > 0:
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
            by_league.setdefault(lname, []).append(f"{h} vs {a}")
        if by_league:
            msg = f"🟢 TODAY'S FIXTURES - {today_str}\n📅 {now.strftime('%A %d %B')}\n\n"
            for lname, games in by_league.items():
                msg += f"{lname} ({len(games)})\n"
                for g in games[:6]:
                    msg += f"• {g}\n"
                msg += "\n"
            msg += f"Total: {len(events)} matches 🟢"
            if fb_post(msg):
                state["daily_date"] = today_str
                posted+=1

    for ev in events:
        ev_id = ev.get("id")
        comp = ev["_league_name"]
        comps = ev.get("competitions", [])
        if not comps: continue
        c = comps[0]
        status = c.get("status", {}).get("type", {})
        s_name = status.get("name", "")
        competitors = c.get("competitors", [])
        if len(competitors) < 2: continue
        home = next((x for x in competitors if x.get("homeAway")=="home"), competitors[0])
        away = next((x for x in competitors if x.get("homeAway")=="away"), competitors[-1])
        h_team = home.get("team", {}).get("displayName","Home")
        a_team = away.get("team", {}).get("displayName","Away")
        h_score = home.get("score","0")
        a_score = away.get("score","0")
        if s_name == "STATUS_FINAL" and ev_id not in state["ft"]:
            msg = f"🟢 FULL TIME - {comp}\n\n{h_team} {h_score} - {a_score} {a_team}\n\n✅ FT 🟢"
            if fb_post(msg):
                state["ft"][ev_id]=True
                posted+=1

    print(f"V20.4 Done - Posted:{posted} Events:{len(events)}")
    save_state(state)

if __name__ == "__main__":
    main()
