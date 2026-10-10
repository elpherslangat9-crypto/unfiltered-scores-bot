import os, requests, json, time
from datetime import datetime, timezone

BRAND = "🟢 Unfiltered Scores"
TAGLINE = "No Filters, Just Football"
HASHTAGS = "#UnfilteredScores #LiveFootball"
FB_PAGE_ID = os.getenv("FB_PAGE_ID", "1293090263895541")
FB_TOKEN = os.getenv("FB_PAGE_TOKEN") or os.getenv("FB_TOKEN")
STATE_FILE = "posted_events.json"

# 🌍 WORLDWIDE LEAGUES - Balanced to avoid ESPN block
ALL_LEAGUES = [
    "eng.1", "eng.2", "eng.fa", "esp.1", "esp.2", "ita.1", "ger.1", "fra.1",
    "ned.1", "por.1", "bel.1", "tur.1", "sco.1", "usa.1", "mex.1", "bra.1", "arg.1",
    "uefa.champions", "uefa.europa", "uefa.europa_conference",
    "caf.champions", "rsa.1", "egy.1", "sau.1", "fifa.world"
]

def bold(t):
    normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    bolded = "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"
    return t.translate(str.maketrans(normal, bolded))

def fb_post(msg):
    if not FB_TOKEN:
        print("FB NO TOKEN")
        return False
    url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed"
    print(f"FB TRY - PageID:{FB_PAGE_ID} TokenLen:{len(FB_TOKEN)}")
    try:
        r = requests.post(url, data={"message": msg, "access_token": FB_TOKEN}, timeout=20)
        print(f"FB {r.status_code}: {r.text[:400]}")
        if r.status_code == 200:
            print(f"FB OK {r.json().get('id')}")
            return True
        return False
    except Exception as e:
        print(f"FB EXC {e}")
        return False

def load_state():
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {"events": [], "lineups": [], "ft": [], "ht": [], "news": [], "transfers": [], "daily": []}

def save_state(s):
    with open(STATE_FILE, 'w') as f:
        json.dump(s, f)

def espn_get(url):
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return {}

def main():
    state = load_state()
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y%m%d")
    hour_eat = (now.hour + 3) % 24
    print(f"V17 LIVE BOT - {today} EAT:{hour_eat}h Leagues:{len(ALL_LEAGUES)}")

    live_found = 0
    all_today_games = []

    for league_code in ALL_LEAGUES:
        data = espn_get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/scoreboard?dates={today}")
        events = data.get("events", [])
        if not events:
            continue

        for ev in events:
            eid = ev['id']
            comp = ev['competitions'][0]
            status_state = ev['status']['type']['state']
            status_detail = ev['status']['type']['detail']
            league_name = ev.get('league', {}).get('name', league_code)

            try:
                home_c = next(c for c in comp['competitors'] if c['homeAway'] == 'home')
                away_c = next(c for c in comp['competitors'] if c['homeAway'] == 'away')
            except:
                home_c = comp['competitors'][0]
                away_c = comp['competitors'][1]

            home = home_c['team']['displayName']
            away = away_c['team']['displayName']
            hg = home_c.get('score', '0')
            ag = away_c.get('score', '0')

            try:
                ko = datetime.fromisoformat(ev['date'].replace("Z", "+00:00"))
                mins_to_ko = (ko - now).total_seconds() / 60
                ko_eat = f"{(ko.hour + 3) % 24:02d}:{ko.minute:02d}"
            except:
                mins_to_ko = 9999
                ko_eat = ""

            if status_state == "pre":
                all_today_games.append(f"⚽ {bold(home)} vs {bold(away)} | {league_name} | {ko_eat} EAT")

            # 1. LINEUPS 5-75 mins before
            if 5 <= mins_to_ko <= 75 and eid not in state["lineups"]:
                summary = espn_get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/summary?event={eid}")
                rosters = summary.get("rosters", [])
                if rosters:
                    msg = f"{BRAND}\n{bold('LINEUPS ARE IN!')}\n━━━━━━━━━━━━━━\n{bold(home)} vs {bold(away)}\n🏆 {league_name}\n🕒 KO {ko_eat} EAT\n\n"
                    for roster in rosters[:2]:
                        tname = bold(roster['team']['displayName'])
                        msg += f"{tname} XI:\n"
                        starters = [p for p in roster.get('roster', []) if p.get('starter')][:11]
                        for p in starters:
                            msg += f"• {p['athlete']['displayName']}\n"
                        msg += "\n"
                    msg += f"{TAGLINE} 🟢\n{HASHTAGS} #Lineups"
                    if fb_post(msg):
                        state["lineups"].append(eid)
                        save_state(state)
                        return

            # 2. LIVE GOALS, RED CARDS
            if status_state == "in":
                live_found += 1
                summary = espn_get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/summary?event={eid}")
                key_events = summary.get("keyEvents", [])

                for ke in key_events:
                    ke_id = ke.get('id', '')
                    ke_type = ke.get('type', {}).get('text', '')
                    clock = ke.get('clock', {}).get('displayValue', '')
                    athlete = ke.get('athlete', {}).get('displayName', '')
                    team_name = ke.get('team', {}).get('displayName', '')
                    uniq = f"{eid}-{ke_id}-{ke_type}-{clock}"

                    if uniq in state["events"]:
                        continue

                    if "Goal" in ke_type:
                        msg = f"{BRAND}\n{bold('GOOOAL!!!')}\n━━━━━━━━━━━━━━\n{bold(home)} {hg} - {ag} {bold(away)}\n⚽ {bold(athlete)} {clock}'\n🏆 {league_name} | ⏱️ {clock}'\n\n{bold('LIVE')} on {TAGLINE} 🟢\n\n{HASHTAGS} #Goal"
                        if fb_post(msg):
                            state["events"].append(uniq)
                            save_state(state)
                            return

                    if "Red" in ke_type and "Card" in ke_type:
                        msg = f"{BRAND}\n{bold('RED CARD! 🟥')}\n━━━━━━━━━━━━━━\n{bold(athlete)} ({team_name})\n{bold(home)} {hg} - {ag} {bold(away)} | {clock}'\n🏆 {league_name}\n\n{HASHTAGS} #RedCard"
                        if fb_post(msg):
                            state["events"].append(uniq)
                            save_state(state)
                            return

                if "Halftime" in status_detail and eid not in state["ht"]:
                    msg = f"{BRAND}\n{bold('HALF TIME')}\n━━━━━━━━━━━━━━\n{bold(home)} {hg} - {ag} {bold(away)}\n🏆 {league_name}\n\nSecond half soon! 🟢\n\n{HASHTAGS} #HT"
                    if fb_post(msg):
                        state["ht"].append(eid)
                        save_state(state)
                        return

            # 3. FULL TIME + SCORERS
            if status_state == "post" and eid not in state["ft"]:
                summary = espn_get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/summary?event={eid}")
                details = summary.get("keyEvents", [])
                msg = f"{BRAND}\n{bold('FULL TIME')}\n━━━━━━━━━━━━━━\n{bold(home)} {hg} - {ag} {bold(away)}\n🏆 {league_name}\n\n"
                scorers = [f"• {d.get('athlete',{}).get('displayName','')} {d.get('clock',{}).get('displayValue','')}'" for d in details if "Goal" in (d.get('type',{}).get('text','') or "")]
                if scorers:
                    msg += f"{bold('SCORERS:')}\n" + "\n".join(scorers[:8]) + "\n\n"
                msg += f"{bold('FT')} | {TAGLINE} 🟢\n\n{HASHTAGS} #FT"
                if fb_post(msg):
                    state["ft"].append(eid)
                    save_state(state)
                    return

        time.sleep(0.25)

    # 4. DAILY FIXTURES - Only if no live games
    if live_found == 0 and hour_eat in [7, 8, 9] and f"daily-{today}" not in state["daily"]:
        if all_today_games:
            msg = f"{BRAND}\n{bold(f'TODAY IN WORLD FOOTBALL')}\n━━━━━━━━━━━━━━\n{today} | {len(all_today_games)} Games | {TAGLINE}\n\n"
            msg += "\n".join(all_today_games[:20]) + "\n\n"
            if len(all_today_games) > 20:
                msg += f"+ {len(all_today_games)-20} more games worldwide...\n\n"
            msg += f"Lineups 1hr before KO + LIVE goals! 🟢\n\n{HASHTAGS} #WorldFootball"
            if fb_post(msg):
                state["daily"].append(f"daily-{today}")
                save_state(state)
                return

    # 5. TRANSFERS & INTERVIEWS
    if hour_eat in [10, 19]:
        for news_league in ["eng.1", "esp.1"]:
            news = espn_get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{news_league}/news?limit=12")
            for art in news.get("articles", [])[:6]:
                nid = str(art.get("id"))
                headline = art.get("headline", "")
                low = headline.lower()
                is_transfer = any(w in low for w in ["transfer", "sign", "joins", "deal", "bid", "here we go"])
                is_interview = any(w in low for w in ["says", "interview", "admits", "reveals", "insists"])

                if is_transfer and nid not in state["transfers"]:
                    msg = f"{BRAND}\n{bold('TRANSFER UPDATE 🔄')}\n━━━━━━━━━━━━━━\n{headline}\n\n{art.get('description','')[:220]}\n\n{TAGLINE} 🟢\n\n{HASHTAGS} #Transfers"
                    if fb_post(msg):
                        state["transfers"].append(nid)
                        save_state(state)
                        return

                if is_interview and nid not in state["news"]:
                    msg = f"{BRAND}\n{bold('INTERVIEW 🎙️')}\n━━━━━━━━━━━━━━\n{headline}\n\n{art.get('description','')[:250]}\n\n{TAGLINE} 🟢\n\n{HASHTAGS} #Interview"
                    if fb_post(msg):
                        state["news"].append(nid)
                        save_state(state)
                        return

    print(f"V17 Done - Live:{live_found} Pre:{len(all_today_games)} - No new events")
    save_state(state)

if __name__ == "__main__":
    main()
