import requests, os, time
from datetime import datetime

API_KEY = os.environ.get('API_FOOTBALL_KEY')
FB_PAGE_ID = os.environ.get('FB_PAGE_ID')
FB_TOKEN = os.environ.get('FB_TOKEN')
HEADERS = {"x-apisports-key": API_KEY}
BASE = "https://v3.football.api-sports.io"

def bold(t):
    a="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    b="𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"
    try: return t.translate(str.maketrans(a,b))
    except: return t

def post_fb(msg):
    try:
        r=requests.post(f"https://graph.facebook.com/{FB_PAGE_ID}/feed", data={"message":msg,"access_token":FB_TOKEN}, timeout=15)
        print(f"POSTED {r.status_code}: {msg[:80]}")
        return r.status_code==200
    except Exception as e:
        print(f"ERR {e}")
        return False

posted=set()
last_lineup=0
last_transfer=0

print("🟢 UNFILTERED SCORES - TEXT ONLY - STARTED")

while True:
    try:
        # 1. LIVE GAMES - ALL WORLD INCLUDING KPL 324
        r=requests.get(f"{BASE}/fixtures?live=all", headers=HEADERS, timeout=15).json()
        lives=r.get('response',[])
        print(f"🟢 Live: {len(lives)} | {datetime.now().strftime('%H:%M')}")

        for f in lives:
            fid=f['fixture']['id']
            league=f['league']['name']
            lid=f['league']['id']
            home=f['teams']['home']['name']
            away=f['teams']['away']['name']
            gh=f['goals']['home']; ga=f['goals']['away']
            minute=f['fixture']['status']['elapsed']
            status=f['fixture']['status']['short']
            minute_str=f"{minute}'" if minute else "LIVE"

            # KPL BRANDING
            is_kpl = lid==324 or "Kenya" in league
            tag = "🟢 #KPL #FKFPL" if is_kpl else "🟢 #UnfilteredScores"
            if is_kpl:
                if "Gor Mahia" in home+away: tag+=" #GorMahia"
                if "AFC Leopards" in home+away: tag+=" #AFCLeopards"
                if "Tusker" in home+away: tag+=" #TuskerFC"

            # GOAL - with scorer
            key_score=f"{fid}_{gh}-{ga}"
            if key_score not in posted and gh is not None:
                # get scorer name
                scorer="GOAL"
                try:
                    ev=requests.get(f"{BASE}/fixtures/events?fixture={fid}", headers=HEADERS, timeout=10).json()
                    for e in reversed(ev.get('response',[])):
                        if e['type']=='Goal':
                            scorer=e['player']['name']
                            minute_str=f"{e['time']['elapsed']}'"
                            break
                except: pass

                msg=f"🟢 {bold('GOOOOAL!!!')} | {bold(minute_str)} | {league}\n\n{bold(home)} {gh}-{ga} {bold(away)}\n\n⚽ Scorer: {bold(scorer)}\n\nWho wins this now? Predict! 👇\n\n{tag} #Live #Goal"
                if post_fb(msg): posted.add(key_score)
                time.sleep(2)

            # RED CARD & PENALTY - real events
            try:
                ev=requests.get(f"{BASE}/fixtures/events?fixture={fid}", headers=HEADERS, timeout=10).json()
                for e in ev.get('response',[]):
                    if e['type']=='Card' and 'Red' in e['detail']:
                        pid=f"{fid}_RED_{e['player']['id']}_{e['time']['elapsed']}"
                        if pid not in posted:
                            msg=f"🟢 {bold('RED CARD!')} {e['time']['elapsed']}' | {league}\n\n{bold(e['player']['name'])} ({e['team']['name']})\n\n{bold(home)} {gh}-{ga} {bold(away)}\n\nGame changed! Sent OFF! 🟥\n\nThoughts? 👇\n\n{tag} #RedCard"
                            if post_fb(msg): posted.add(pid)
                    if 'Penalty' in e['detail'] or e['type']=='Penalty':
                        pid=f"{fid}_PEN_{e['time']['elapsed']}_{e['player']['id']}"
                        if pid not in posted:
                            msg=f"🟢 {bold('PENALTY!')} {e['time']['elapsed']}' | {league}\n\n{home} {gh}-{ga} {away}\n\n{e['player']['name']} - {e['detail']}\n\nScored or missed? 👇\n\n{tag} #Penalty"
                            if post_fb(msg): posted.add(pid)
            except: pass

            # HT / FT - once only
            if status=='HT':
                pid=f"{fid}_HT_{gh}-{ga}"
                if pid not in posted:
                    msg=f"🟢 {bold('HALF-TIME')} | {league}\n\n{bold(home)} {gh}-{ga} {bold(away)}\n\nYour thoughts on first half? 👇\n\n{tag} #HT"
                    if post_fb(msg): posted.add(pid)
            if status=='FT':
                pid=f"{fid}_FT_{gh}-{ga}"
                if pid not in posted:
                    msg=f"🟢 {bold('FULL-TIME')} | {league}\n\n{bold(home)} {gh}-{ga} {bold(away)}\n\nRate this game 1-10! 👇\n\n{tag} #FT"
                    if post_fb(msg): posted.add(pid)

        # 2. LINEUP DROP - 1 hour before
        if time.time()-last_lineup>1800:
            try:
                today=datetime.utcnow().strftime('%Y-%m-%d')
                r=requests.get(f"{BASE}/fixtures?date={today}&timezone=Africa/Nairobi", headers=HEADERS, timeout=15).json()
                for f in r.get('response',[])[:30]:
                    if f['fixture']['status']['short']!='NS': continue
                    fid=f['fixture']['id']
                    pid=f"{fid}_LINEUP"
                    if pid in posted: continue
                    # check if lineup ready
                    lr=requests.get(f"{BASE}/fixtures/lineups?fixture={fid}", headers=HEADERS, timeout=10).json()
                    if lr.get('response'):
                        league=f['league']['name']; home=f['teams']['home']['name']; away=f['teams']['away']['name']
                        msg=f"🟢 {bold('LINEUP DROP!')} | {league}\n\n{bold(home)} vs {bold(away)}\n\nStarting XIs are OUT! Kickoff soon.\n\nWho wins? Predict! 👇\n\n#Lineup #BuildUp 🟢 #UnfilteredScores"
                        if post_fb(msg): posted.add(pid); last_lineup=time.time(); break
            except Exception as e:
                print(f"LINEUP ERR {e}")

        # 3. BREAKING TRANSFERS - when no live
        if len(lives)==0 and time.time()-last_transfer>3600:
            try:
                today=datetime.utcnow().strftime('%Y-%m-%d')
                tr=requests.get(f"{BASE}/transfers?date={today}", headers=HEADERS, timeout=15).json()
                if tr.get('response'):
                    t=tr['response'][0]
                    player=t['player']['name']
                    to_team=t['transfers'][0]['teams']['in']['name'] if t['transfers'] else "New Club"
                    from_team=t['transfers'][0]['teams']['out']['name'] if t['transfers'] else ""
                    msg=f"🟢 {bold('BREAKING:')} {bold('TRANSFER NEWS')}\n\n{bold(player)} \n{from_team} ➡️ {to_team}\n\nDone deal? Yes or No? 👇\n\n#Transfer #Breaking 🟢 #UnfilteredScores"
                    if post_fb(msg): last_transfer=time.time()
            except Exception as e:
                print(f"TRANSFER ERR {e}")

        time.sleep(35 if lives else 90)

    except Exception as e:
        print(f"LOOP ERR {e}")
        time.sleep(30)
