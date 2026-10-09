import requests, os, json, time
from datetime import datetime

# Support BOTH secret names so it never fails
API_KEY = os.environ.get('API_KEY') or os.environ.get('API_FOOTBALL_KEY')
FB_PAGE_ID = os.environ.get('FB_PAGE_ID')
FB_TOKEN = os.environ.get('FB_PAGE_TOKEN') or os.environ.get('FB_TOKEN')
HEADERS = {"x-apisports-key": API_KEY}
BASE = "https://v3.football.api-sports.io"
STATE_FILE = "posted.json"

def bold(t):
    a="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    b="𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"
    try: return t.translate(str.maketrans(a,b))
    except: return t

def load_posted():
    try:
        with open(STATE_FILE,'r') as f: return set(json.load(f))
    except: return set()

def save_posted(s):
    try:
        with open(STATE_FILE,'w') as f: json.dump(list(s)[-1000:], f)
    except: pass

def post_fb(msg):
    try:
        r=requests.post(f"https://graph.facebook.com/{FB_PAGE_ID}/feed", data={"message":msg,"access_token":FB_TOKEN}, timeout=20)
        print(f"POST {r.status_code}: {msg[:90]}")
        return r.status_code==200
    except Exception as e:
        print(f"FB ERR {e}")
        return False

posted = load_posted()
print(f"🟢 UNFILTERED V3-24/7 PERFECTED | Memory {len(posted)} | {datetime.now()}")

# Safety check
if not API_KEY or not FB_PAGE_ID or not FB_TOKEN:
    print("❌ MISSING SECRETS! Check API_KEY, FB_PAGE_ID, FB_PAGE_TOKEN")
    time.sleep(10)
    exit(1)

while True:
    try:
        r = requests.get(f"{BASE}/fixtures?live=all", headers=HEADERS, timeout=20).json()
        lives = r.get('response', [])
        lives = sorted(lives, key=lambda x: (0 if x['league']['id']==324 else 1)) # KPL 324 FIRST
        print(f"🟢 Live: {len(lives)} | {datetime.now().strftime('%H:%M:%S')}")

        for f in lives[:6]: # max 6 games per cycle to save API
            fid = f['fixture']['id']
            league = f['league']['name']; lid = f['league']['id']
            home = f['teams']['home']['name']; away = f['teams']['away']['name']
            gh = f['goals']['home']; ga = f['goals']['away']
            status = f['fixture']['status']['short']
            minute = f['fixture']['status']['elapsed'] or 0

            is_kpl = lid==324 or "Kenya" in league
            tag = "🟢 #KPL #FKFPL #UnfilteredScores" if is_kpl else "🟢 #UnfilteredScores #LiveScore"
            if is_kpl:
                if "Gor" in home+away: tag+=" #GorMahia #Sirkal"
                if "Leopards" in home+away: tag+=" #AFCLeopards #Ingwe"
                hook = "Nani atashinda hii? Predict! 👇 Mambo iko aje?"
            else:
                hook = "Who wins this now? Predict! 👇"

            # ONE API CALL ONLY for all events
            try:
                ev_data = requests.get(f"{BASE}/fixtures/events?fixture={fid}", headers=HEADERS, timeout=12).json().get('response',[])
            except:
                ev_data = []
                time.sleep(1)

            for e in ev_data[-8:]: # last 8 events only
                etype = e.get('type',''); detail = e.get('detail',''); t = e['time']['elapsed']; pid = e['player']['id']
                team = e['team']['name']

                if etype=='Goal':
                    key = f"{fid}_GOAL_{pid}_{t}_{gh}-{ga}"
                    if key not in posted:
                        scorer = e['player']['name']
                        msg = f"🟢 {bold('GOOOOAL!!!')} | {bold(f'{t}')} | {league}\n\n{bold(home)} {gh}-{ga} {bold(away)}\n\n⚽ Scorer: {bold(scorer)} - {detail}\n\n{hook}\n\n{tag} #Goal"
                        if post_fb(msg): posted.add(key); save_posted(posted); time.sleep(2)

                if etype=='Card' and 'Red' in detail:
                    key = f"{fid}_RED_{pid}_{t}"
                    if key not in posted:
                        msg = f"🟢 {bold('RED CARD!')} {t}' | {league}\n\n{bold(e['player']['name'])} ({team}) sent OFF! 🟥\n\n{bold(home)} {gh}-{ga} {bold(away)}\n\nGame changed! Thoughts? 👇\n\n{tag} #RedCard"
                        if post_fb(msg): posted.add(key); save_posted(posted)

                if 'Penalty' in detail:
                    key = f"{fid}_PEN_{pid}_{t}"
                    if key not in posted:
                        msg = f"🟢 {bold('PENALTY!')} {t}' | {league}\n\n{home} {gh}-{ga} {away}\n\n{e['player']['name']} - {detail} ({team})\n\nScored or missed? 👇\n\n{tag} #Penalty"
                        if post_fb(msg): posted.add(key); save_posted(posted)

                if 'Own Goal' in detail or 'VAR' in detail:
                    key = f"{fid}_VAR_{pid}_{t}"
                    if key not in posted:
                        msg = f"🟢 {bold('DRAMA!')} {t}' | {league}\n\n{detail}: {e['player']['name']} ({team})\n\n{bold(home)} {gh}-{ga} {bold(away)}\n\n😱 What a moment!\n\n{tag}"
                        if post_fb(msg): posted.add(key); save_posted(posted)

            # HT / FT
            if status=='HT':
                key = f"{fid}_HT_{gh}-{ga}"
                if key not in posted:
                    if post_fb(f"🟢 {bold('HALF-TIME')} | {league}\n\n{bold(home)} {gh}-{ga} {bold(away)}\n\nYour thoughts on first half? 👇\n\n{tag} #HT"): posted.add(key); save_posted(posted)
            if status=='FT':
                key = f"{fid}_FT_{gh}-{ga}"
                if key not in posted:
                    if post_fb(f"🟢 {bold('FULL-TIME')} | {league}\n\n{bold(home)} {gh}-{ga} {bold(away)}\n\nRate this game 1-10! 👇\n\n{tag} #FT"): posted.add(key); save_posted(posted)

        # LINEUP + TRANSFER only when no live to save API
        if len(lives)==0:
            try:
                today = datetime.utcnow().strftime('%Y-%m-%d')
                fixtures = requests.get(f"{BASE}/fixtures?date={today}&timezone=Africa/Nairobi", headers=HEADERS, timeout=15).json().get('response',[])
                for fx in fixtures[:15]:
                    if fx['fixture']['status']['short']!='NS': continue
                    fid = fx['fixture']['id']
                    key = f"{fid}_LINEUP"
                    if key in posted: continue
                    lr = requests.get(f"{BASE}/fixtures/lineups?fixture={fid}", headers=HEADERS, timeout=10).json().get('response',[])
                    if lr:
                        league=fx['league']['name']; home=fx['teams']['home']['name']; away=fx['teams']['away']['name']
                        msg=f"🟢 {bold('LINEUP DROP!')} | {league}\n\n{bold(home)} vs {bold(away)}\n\nStarting XIs are OUT! Kickoff soon.\n\nWho wins? Predict! 👇\n\n#Lineup 🟢 #UnfilteredScores"
                        if post_fb(msg): posted.add(key); save_posted(posted); break
            except Exception as e: print(f"LINEUP ERR {e}")

            # BREAKING TRANSFER
            try:
                today = datetime.utcnow().strftime('%Y-%m-%d')
                tr = requests.get(f"{BASE}/transfers?date={today}", headers=HEADERS, timeout=15).json().get('response',[])
                if tr:
                    t=tr[0]; player=t['player']['name']
                    trans=t['transfers'][0] if t['transfers'] else None
                    to_team=trans['teams']['in']['name'] if trans else "New Club"
                    from_team=trans['teams']['out']['name'] if trans else ""
                    key=f"TRANSFER_{player}_{today}"
                    if key not in posted:
                        msg=f"🟢 {bold('BREAKING: TRANSFER NEWS')}\n\n{bold(player)}\n{from_team} ➡️ {to_team}\n\nDone deal? Yes or No? 👇\n\n#Transfer #Breaking 🟢 #UnfilteredScores"
                        if post_fb(msg): posted.add(key); save_posted(posted)
            except Exception as e: print(f"TRANSFER ERR {e}")

            # Keep alive post if nothing else
            if len(lives)==0 and len([k for k in posted if datetime.utcnow().strftime('%Y-%m-%d') in k])==0:
                pass # don't spam when no games

        save_posted(posted)
        time.sleep(40 if lives else 120) # 40 sec when live, 2 mins when no live = saves API + minutes

    except Exception as e:
        print(f"LOOP ERR {e}")
        time.sleep(30)
