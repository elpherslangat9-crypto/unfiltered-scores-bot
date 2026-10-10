import os, requests, json, time, re, html
from datetime import datetime, timezone

BRAND = "🟢"
TAGLINE = "No Filters, Just Football"
HASHTAGS = "#UnfilteredScores #LiveFootball"
FB_PAGE_ID = os.getenv("FB_PAGE_ID", "1293090263895541")
FB_TOKEN = os.getenv("FB_PAGE_TOKEN") or os.getenv("FB_TOKEN")
STATE_FILE = "posted_events.json"

ALL_LEAGUES = [
    "eng.1", "eng.2", "esp.1", "ita.1", "ger.1", "fra.1",
    "ned.1", "por.1", "bel.1", "tur.1", "usa.1", "mex.1", "bra.1", "arg.1",
    "uefa.champions", "uefa.europa", "uefa.europa_conference",
    "caf.champions", "rsa.1", "egy.1", "sau.1"
]

# BREAKING KEYWORDS - same as MatchCorner uses from FTotal
BREAKING_KEYWORDS = [
    "suspended", "abandoned", "postponed", "interrupted", "paused", "delayed",
    "fans throwing", "paper objects", "pitch invasion", "fans on pitch",
    "protest", "locker rooms", "players sent off", "sent to locker",
    "VAR overturn", "VAR check", "game stopped", "match stopped",
    "floodlight", "power failure", "bottle thrown", "objects thrown"
]

def bold(t):
    normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    bolded = "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"
    return t.translate(str.maketrans(normal, bolded))

def fb_post(msg):
    if not FB_TOKEN: return False
    url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed"
    try:
        r = requests.post(url, data={"message": msg, "access_token": FB_TOKEN}, timeout=20)
        print(f"FB {r.status_code}: {r.text[:400]}")
        return r.status_code == 200
    except Exception as e:
        print(f"FB EXC {e}"); return False

def load_state():
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE,'r') as f: return json.load(f)
    except: pass
    return {"events":[],"lineups":[],"ft":[],"ht":[],"news":[],"transfers":[],"daily":[],"breaking":[]}

def save_state(s):
    with open(STATE_FILE,'w') as f: json.dump(s,f)

def espn_get(url):
    try:
        r=requests.get(url, timeout=15, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code==200: return r.json()
    except: pass
    return {}

def get_scorer_name(d):
    name = d.get('athlete',{}).get('displayName','')
    if not name:
        parts = d.get('participants',[])
        if parts:
            name = parts[0].get('athlete',{}).get('displayName','')
    if not name:
        txt = d.get('text','') or d.get('type',{}).get('text','')
        if ' - ' in txt:
            name = txt.split(' - ')[-1].split('(')[0].strip()
        else:
            name = txt[:30]
    return name.strip() or "Goal"

def check_breaking_incident(eid, league_code, home, away, league_name):
    """NEW LAYER - Scans commentary for incidents like Vallecano case"""
    try:
        summary = espn_get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/summary?event={eid}")
        # Check commentary
        commentary = summary.get("commentary",[]) + summary.get("keyEvents",[])
        for c in commentary[-8:]: # last 8 events
            text = (c.get('text','') + " " + c.get('type',{}).get('text','')).lower()
            for kw in BREAKING_KEYWORDS:
                if kw.lower() in text:
                    clean_text = c.get('text','') or c.get('type',{}).get('text','')
                    clock = c.get('clock',{}).get('displayValue','') or c.get('time',{}).get('displayValue','')
                    return f"{clean_text} {clock}'".strip()
        # Check situation text
        situation = summary.get("header",{}).get("competitions",[{}])[0].get("situation",{}).get("description","")
        if situation:
            low = situation.lower()
            for kw in BREAKING_KEYWORDS:
                if kw.lower() in low:
                    return situation
    except: pass
    return None

def main():
    state=load_state()
    now=datetime.now(timezone.utc)
    today=now.strftime("%Y%m%d")
    hour_eat=(now.hour+3)%24
    print(f"V19 BREAKING LAYER - {today} EAT:{hour_eat}h")

    live_found=0
    all_games=[]

    for league_code in ALL_LEAGUES:
        data=espn_get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/scoreboard?dates={today}")
        for ev in data.get("events",[]):
            eid=ev['id']
            comp=ev['competitions'][0]
            status_state=ev['status']['type']['state']
            status_detail=ev['status']['type']['detail']
            league_name=ev.get('league',{}).get('name',league_code)

            try:
                home_c=next(c for c in comp['competitors'] if c['homeAway']=='home')
                away_c=next(c for c in comp['competitors'] if c['homeAway']=='away')
            except:
                home_c=comp['competitors'][0]
                away_c=comp['competitors'][1]

            home=home_c['team']['displayName']
            away=away_c['team']['displayName']
            hg=home_c.get('score','0')
            ag=away_c.get('score','0')

            try:
                ko=datetime.fromisoformat(ev['date'].replace("Z","+00:00"))
                mins_to_ko=(ko-now).total_seconds()/60
                ko_eat=f"{(ko.hour+3)%24:02d}:{ko.minute:02d}"
            except:
                mins_to_ko=9999
                ko_eat=""

            if status_state=="pre":
                all_games.append(f"{home} vs {away} | {league_name} | {ko_eat} EAT")

            # LINEUPS ONE ROW
            if 5 <= mins_to_ko <= 75 and eid not in state["lineups"]:
                summary=espn_get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/summary?event={eid}")
                rosters=summary.get("rosters",[])
                if rosters:
                    msg = f"{bold('LINEUPS ARE IN!')}\n{home} vs {away}\n🏆 {league_name} | 🕒 {ko_eat} EAT\n━━━━━━━━━━━━━━\n"
                    for roster in rosters[:2]:
                        tname=roster['team']['displayName']
                        starters=[p['athlete']['displayName'] for p in roster.get('roster',[]) if p.get('starter')][:11]
                        if starters:
                            msg += f"\n{tname} XI: {', '.join(starters)}\n"
                    msg += f"\n{TAGLINE} {BRAND}\n{HASHTAGS} #Lineups"
                    if fb_post(msg):
                        state["lineups"].append(eid); save_state(state); return

            # LIVE + BREAKING LAYER
            if status_state=="in":
                live_found+=1

                # ===== NEW: BREAKING INCIDENTS CHECK =====
                if eid not in state["breaking"]:
                    incident_text = check_breaking_incident(eid, league_code, home, away, league_name)
                    if incident_text:
                        msg = f" {bold('BREAKING:')} {home} vs {away} - {incident_text}\n\n{home} {hg} - {ag} {away}\n🏆 {league_name}\n\nSource: Live Commentary\n\n{TAGLINE} {BRAND}\n{HASHTAGS} #BreakingNews"
                        if fb_post(msg):
                            state["breaking"].append(eid); save_state(state); return

                summary=espn_get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/summary?event={eid}")
                for ke in summary.get("keyEvents",[]):
                    ke_id=ke.get('id','')
                    ke_type=ke.get('type',{}).get('text','')
                    clock=ke.get('clock',{}).get('displayValue','')
                    athlete=get_scorer_name(ke)
                    uniq=f"{eid}-{ke_id}-{ke_type}-{clock}"
                    if uniq in state["events"]: continue
                    if "Goal" in ke_type:
                        msg = f"{bold('GOOOAL!!!')} {clock}'\n{bold(home)} {hg} - {ag} {bold(away)}\n⚽ {athlete}\n🏆 {league_name}\n\n{TAGLINE} {BRAND}\n{HASHTAGS} #Goal"
                        if fb_post(msg):
                            state["events"].append(uniq); save_state(state); return
                    if "Red" in ke_type:
                        team_name=ke.get('team',{}).get('displayName','')
                        msg = f"{bold('RED CARD! 🟥')} {clock}'\n{athlete} ({team_name})\n{home} {hg} - {ag} {away} | {league_name}\n\n{HASHTAGS} #RedCard"
                        if fb_post(msg):
                            state["events"].append(uniq); save_state(state); return
                if "Halftime" in status_detail and eid not in state["ht"]:
                    msg = f"{bold('HALF TIME')}\n{home} {hg} - {ag} {away}\n🏆 {league_name}\n\n{HASHTAGS} #HT"
                    if fb_post(msg):
                        state["ht"].append(eid); save_state(state); return

            if status_state=="post" and eid not in state["ft"]:
                summary=espn_get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/summary?event={eid}")
                details=summary.get("keyEvents",[])
                msg = f"{bold('FULL TIME')}\n{bold(home)} {hg} - {ag} {bold(away)}\n🏆 {league_name}\n\n"
                scorers=[]
                for d in details:
                    if "Goal" in (d.get('type',{}).get('text','') or ""):
                        name=get_scorer_name(d)
                        clock=d.get('clock',{}).get('displayValue','')
                        scorers.append(f"• {name} {clock}'")
                if scorers:
                    msg += f"{bold('SCORERS:')}\n" + "\n".join(scorers[:10]) + "\n\n"
                msg += f"{bold('FT')} | {TAGLINE} {BRAND}\n\n{HASHTAGS} #FT"
                if fb_post(msg):
                    state["ft"].append(eid); save_state(state); return
        time.sleep(0.25)

    if live_found==0 and hour_eat in [7,8,9] and f"daily-{today}" not in state["daily"]:
        if all_games:
            msg = f"{bold('TODAY FIXTURES')} - {len(all_games)} Games\n━━━━━━━━━━━━━━\n" + "\n".join(all_games[:22]) + f"\n\n{TAGLINE} {BRAND}\n{HASHTAGS}"
            if fb_post(msg):
                state["daily"].append(f"daily-{today}"); save_state(state); return

    print(f"V19 Done Live:{live_found} Pre:{len(all_games)}")
    save_state(state)

if __name__=="__main__":
    main()
