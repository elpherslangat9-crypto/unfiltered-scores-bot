import os, requests, json, time
from datetime import datetime, timezone

BRAND = "🟢 Unfiltered Scores"
TAGLINE = "No Filters, Just Football"
HASHTAGS = "#UnfilteredScores #LiveFootball"
FB_PAGE_ID = os.getenv("FB_PAGE_ID", "61595099671352")
FB_TOKEN = os.getenv("FB_PAGE_TOKEN") or os.getenv("FB_TOKEN")
STATE_FILE = "posted_events.json"

# 🌍 ALL LEAGUES IN THE WORLD - ESPN CODES
ALL_LEAGUES = [
    # EUROPE TOP
    "eng.1", "eng.2", "eng.3", "eng.4", "eng.fa", "eng.league_cup",
    "esp.1", "esp.2", "esp.copa_del_rey",
    "ita.1", "ita.2", "ita.coppa_italia",
    "ger.1", "ger.2", "ger.dfb_pokal",
    "fra.1", "fra.2", "fra.coupe_de_france",
    "ned.1", "por.1", "bel.1", "tur.1", "sco.1", "rus.1", "ukr.1",
    "gre.1", "aut.1", "sui.1", "den.1", "nor.1", "swe.1", "pol.1", "cze.1",
    "cro.1", "ser.1", "rom.1", "irl.1", "irl.1", "hun.1",
    # EUROPE CUPS
    "uefa.champions", "uefa.europa", "uefa.europa_conference", "uefa.super_cup", "uefa.nations",
    # AMERICAS
    "usa.1", "usa.nwsl", "mex.1", "bra.1", "arg.1", "arg.copa", "chl.1", "col.1", "per.1", "uru.1",
    "conmebol.libertadores", "conmebol.sudamericana",
    # AFRICA - YOUR REGION
    "caf.champions", "caf.confed", "afr.nations", "rsa.1", "egy.1", "nga.1", "ken.1", "uga.1", "tan.1", "mar.1", "alg.1",
    # ASIA + MIDDLE EAST
    "aus.1", "jpn.1", "kor.1", "chn.1", "ind.1", "tha.1", "vie.1",
    "afc.champions", "afc.asian_cup",
    "sau.1", "uae.1", "qat.1", "isr.1",
    # WORLD CUPS
    "fifa.world", "fifa.wwc", "fifa.worldq", "fifa.womens_worldq",
]

def bold(t):
    m="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    b="𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"
    return "".join(b[m.index(c)] if c in m else c for c in t)

def fb_post(msg):
    if not FB_TOKEN: return False
    url=f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed"
    r=requests.post(url, data={"message": msg, "access_token": FB_TOKEN}, timeout=20)
    print(f"FB {r.status_code}")
    return r.status_code==200

def load_state():
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE,'r') as f: return json.load(f)
    except: pass
    return {"events":[],"lineups":[],"ft":[],"ht":[],"news":[],"transfers":[],"daily":[]}

def save_state(s):
    with open(STATE_FILE,'w') as f: json.dump(s,f)

def espn_get(url):
    try:
        r=requests.get(url, timeout=15, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code==200:
            return r.json()
    except: pass
    return {}

def main():
    state=load_state()
    now=datetime.now(timezone.utc)
    today = now.strftime("%Y%m%d")
    hour_eat = (now.hour + 3) % 24
    print(f"V16 WORLDWIDE - {today} - EAT {hour_eat}h - Checking {len(ALL_LEAGUES)} leagues")

    live_found = 0
    pre_found = 0

    # LOOP ALL LEAGUES
    for league_code in ALL_LEAGUES:
        data = espn_get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/scoreboard?dates={today}")
        events = data.get("events", [])
        if not events: continue

        for ev in events:
            eid = ev['id']
            comp = ev['competitions'][0]
            status_state = ev['status']['type']['state'] # pre,in,post
            status_detail = ev['status']['type']['detail']
            status_name = ev['status']['type']['name']

            # Teams
            try:
                home_c = next(c for c in comp['competitors'] if c['homeAway']=='home')
                away_c = next(c for c in comp['competitors'] if c['homeAway']=='away')
            except:
                home_c = comp['competitors'][0]
                away_c = comp['competitors'][1]

            home = home_c['team']['displayName']
            away = away_c['team']['displayName']
            hg = home_c.get('score','0')
            ag = away_c.get('score','0')
            league_name = ev.get('league',{}).get('name', league_code)

            try:
                ko = datetime.fromisoformat(ev['date'].replace("Z","+00:00"))
                mins_to_ko = (ko - now).total_seconds()/60
                ko_eat = f"{(ko.hour+3)%24:02d}:{ko.minute:02d}"
            except:
                mins_to_ko = 9999
                ko_eat = ""

            # ===== 1. LINEUPS (5-75 mins before) =====
            if 5 <= mins_to_ko <= 75 and eid not in state["lineups"]:
                summary = espn_get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/summary?event={eid}")
                rosters = summary.get("rosters", [])
                if rosters:
                    msg = f"{BRAND}\n{bold('LINEUPS ARE IN!')}\n━━━━━━━━━━━━━━\n{bold(home)} vs {bold(away)}\n🏆 {league_name}\n🕒 KO {ko_eat} EAT\n\n"
                    for roster in rosters[:2]:
                        tname = bold(roster['team']['displayName'])
                        msg += f"{tname} XI:\n"
                        starters = [p for p in roster.get('roster',[]) if p.get('starter')][:11]
                        for p in starters:
                            msg += f"• {p['athlete']['displayName']}\n"
                        msg += "\n"
                    msg += f"{TAGLINE} 🟢\n{HASHTAGS} #Lineups"
                    if fb_post(msg):
                        state["lineups"].append(eid); save_state(state); return

            # ===== 2. LIVE - GOALS, RED CARDS, SCORERS =====
            if status_state == "in":
                live_found += 1
                summary = espn_get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/summary?event={eid}")
                key_events = summary.get("keyEvents", []) or summary.get("header",{}).get("competitions",[{}])[0].get("details",[])

                for ke in key_events:
                    ke_id = ke.get('id','')
                    ke_type = ke.get('type',{}).get('text','') or ke.get('type','')
                    clock = ke.get('clock',{}).get('displayValue','') or ke.get('clock','')
                    athlete = ke.get('athlete',{}).get('displayName','') or ke.get('text','')[:40]
                    team_name = ke.get('team',{}).get('displayName','')
                    uniq = f"{eid}-{ke_id}-{ke_type}-{clock}"

                    if uniq in state["events"]: continue

                    # GOAL
                    if "Goal" in ke_type or "goal" in str(ke_type).lower():
                        msg = f"{BRAND}\n{bold('GOOOAL!!!')}\n━━━━━━━━━━━━━━\n{bold(home)} {hg} - {ag} {bold(away)}\n⚽ {bold(athlete)} {clock}'\n🏆 {league_name} | ⏱️ {clock}'\n\n{bold('LIVE')} on {TAGLINE} 🟢\n\n{HASHTAGS} #Goal #{league_name.replace(' ','')}"
                        if fb_post(msg):
                            state["events"].append(uniq); save_state(state); return

                    # RED CARD
                    if "Red" in ke_type and "Card" in ke_type:
                        msg = f"{BRAND}\n{bold('RED CARD! 🟥')}\n━━━━━━━━━━━━━━\n{bold(athlete)} ({team_name})\n{bold(home)} {hg} - {ag} {bold(away)} | {clock}'\n🏆 {league_name}\n\n{HASHTAGS} #RedCard"
                        if fb_post(msg):
                            state["events"].append(uniq); save_state(state); return

                # HALFTIME
                if "Halftime" in status_detail and eid not in state["ht"]:
                    msg = f"{BRAND}\n{bold('HALF TIME')}\n━━━━━━━━━━━━━━\n{bold(home)} {hg} - {ag} {bold(away)}\n🏆 {league_name}\n\nSecond half soon! 🟢\n\n{HASHTAGS} #HT"
                    if fb_post(msg):
                        state["ht"].append(eid); save_state(state); return

            # ===== 3. FULL TIME + SCORERS =====
            if status_state == "post" and eid not in state["ft"]:
                summary = espn_get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/summary?event={eid}")
                msg = f"{BRAND}\n{bold('FULL TIME')}\n━━━━━━━━━━━━━━\n{bold(home)} {hg} - {ag} {bold(away)}\n🏆 {league_name}\n\n"
                # Try get scorers
                details = summary.get("header",{}).get("competitions",[{}])[0].get("details",[]) or summary.get("keyEvents",[])
                scorers = [f"• {d.get('athlete',{}).get('displayName','')} {d.get('clock',{}).get('displayValue','')}'" for d in details if "Goal" in (d.get('type',{}).get('text','') or "")]
                if scorers:
                    msg += f"{bold('SCORERS:')}\n" + "\n".join(scorers[:8]) + "\n\n"
                msg += f"{bold('FT')} | {TAGLINE} 🟢\n\n{HASHTAGS} #FT"
                if fb_post(msg):
                    state["ft"].append(eid); save_state(state); return

            # Pre count for daily roundup
            if status_state == "pre":
                pre_found += 1

        time.sleep(0.3) # Be nice to ESPN

    # ===== 4. DAILY FIXTURES ROUNDUP (if no live) =====
    if live_found==0 and hour_eat in [7,8,9] and f"daily-{today}" not in state["daily"]:
        msg = f"{BRAND}\n{bold(f'TODAY IN WORLD FOOTBALL - {len(ALL_LEAGUES)} LEAGUES')}\n━━━━━━━━━━━━━━\n"
        msg += f"{today} | {TAGLINE}\n\n"
        # Re-fetch to list top games
        top_games = []
        for lc in ["eng.1","esp.1","ita.1","ger.1","fra.1","usa.1","sau.1","ken.1","rsa.1"][:5]:
            d = espn_get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lc}/scoreboard?dates={today}")
            for ev in d.get("events", [])[:2]:
                comp = ev['competitions'][0]
                h = next((c['team']['displayName'] for c in comp['competitors'] if c['homeAway']=='home'), "?")
                a = next((c['team']['displayName'] for c in comp['competitors'] if c['homeAway']=='away'), "?")
                try:
                    ko = datetime.fromisoformat(ev['date'].replace("Z","+00:00"))
                    ko_eat = f"{(ko.hour+3)%24:02d}:{ko.minute:02d}"
                except:
                    ko_eat = ""
                top_games.append(f"⚽ {bold(h)} vs {bold(a)} | {ev.get('league',{}).get('name','')} | {ko_eat} EAT")
        msg += "\n".join(top_games[:12]) + "\n\n"
        msg += f"Lineups 1hr before KO + LIVE goals from ALL leagues! 🟢\n\n{HASHTAGS} #WorldFootball"
        if fb_post(msg):
            state["daily"].append(f"daily-{today}"); save_state(state); return

    # ===== 5. TRANSFERS & INTERVIEWS (from ESPN news) =====
    if hour_eat in [10, 19]:
        for news_league in ["eng.1","esp.1"]:
            news = espn_get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{news_league}/news?limit=15")
            for art in news.get("articles", [])[:5]:
                nid = str(art.get("id"))
                headline = art.get("headline","")
                is_transfer = any(w in headline.lower() for w in ["transfer","sign","joins","deal","bid"])
                is_interview = any(w in headline.lower() for w in ["says","interview","admits","reveals","insists"])

                if is_transfer and nid not in state["transfers"]:
                    msg = f"{BRAND}\n{bold('TRANSFER UPDATE 🔄')}\n━━━━━━━━━━━━━━\n{headline}\n\n{art.get('description','')[:220]}\n\n{TAGLINE} 🟢\n\n{HASHTAGS} #Transfers"
                    if fb_post(msg):
                        state["transfers"].append(nid); save_state(state); return

                if is_interview and nid not in state["news"]:
                    msg = f"{BRAND}\n{bold('INTERVIEW 🎙️')}\n━━━━━━━━━━━━━━\n{headline}\n\n{art.get('description','')[:250]}\n\n{TAGLINE} 🟢\n\n{HASHTAGS} #Interview"
                    if fb_post(msg):
                        state["news"].append(nid); save_state(state); return

    print(f"V16 Done - Live:{live_found} Pre:{pre_found} - All {len(ALL_LEAGUES)} leagues checked - No quota used")
    save_state(state)

if __name__=="__main__":
    main()
