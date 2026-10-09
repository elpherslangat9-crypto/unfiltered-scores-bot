import requests, os, json
from datetime import datetime, timedelta

API_KEY = os.environ.get('API_KEY')
FB_PAGE_ID = os.environ.get('FB_PAGE_ID')
FB_TOKEN = os.environ.get('FB_PAGE_TOKEN')
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
    with open(STATE_FILE,'w') as f: json.dump(list(s)[-800:], f)

def post_fb(msg):
    try:
        r=requests.post(f"https://graph.facebook.com/{FB_PAGE_ID}/feed", data={"message":msg,"access_token":FB_TOKEN}, timeout=20)
        print(f"POST {r.status_code}: {msg[:100]}")
        return r.status_code==200
    except Exception as e:
        print(f"FB ERR {e}"); return False

posted=load_posted()
print(f"🟢 V3 START - Memory {len(posted)}")

# === 1. LIVE GAMES - ALL INCLUDING KPL 324 ===
r=requests.get(f"{BASE}/fixtures?live=all", headers=HEADERS, timeout=15).json()
lives=r.get('response',[])
lives = sorted(lives, key=lambda x: (0 if x['league']['id']==324 else 1)) # KPL first
print(f"Live: {len(lives)}")

for f in lives[:5]: # max 5 games per run = saves API
    fid=f['fixture']['id']
    league=f['league']['name']; lid=f['league']['id']
    home=f['teams']['home']['name']; away=f['teams']['away']['name']
    gh=f['goals']['home']; ga=f['goals']['away']
    status=f['fixture']['status']['short']
    minute=f['fixture']['status']['elapsed'] or 0

    is_kpl = lid==324 or "Kenya" in league
    tag = "🟢 #KPL #FKFPL #UnfilteredScores" if is_kpl else "🟢 #UnfilteredScores #LiveScore"
    if is_kpl:
        if "Gor" in home+away: tag+=" #GorMahia"
        if "Leopards" in home+away: tag+=" #AFCLeopards"
        hook = "Nani atashinda hii? 👇"
    else:
        hook = "Who wins this now? 👇"

    # ONE events call for ALL events
    try:
        ev_data=requests.get(f"{BASE}/fixtures/events?fixture={fid}", headers=HEADERS, timeout=10).json().get('response',[])
    except: ev_data=[]

    for e in ev_data[-6:]: # check last 6 events only
        etype=e.get('type',''); detail=e.get('detail',''); t=e['time']['elapsed']; pid=e['player']['id']

        # GOAL
        if etype=='Goal':
            key=f"{fid}_GOAL_{pid}_{t}_{gh}-{ga}"
            if key not in posted:
                scorer=e['player']['name']
                msg=f"🟢 {bold('GOOOOAL!!!')} | {bold(f'{t}')} | {league}\n\n{bold(home)} {gh}-{ga} {bold(away)}\n\n⚽ Scorer: {bold(scorer)} - {detail}\n\n{hook}\n\n{tag} #Goal"
                if post_fb(msg): posted.add(key)

        # RED CARD
        if etype=='Card' and 'Red' in detail:
            key=f"{fid}_RED_{pid}_{t}"
            if key not in posted:
                msg=f"🟢 {bold('RED CARD!')} {t}' | {league}\n\n{bold(e['player']['name'])} ({e['team']['name']}) sent OFF! 🟥\n\n{bold(home)} {gh}-{ga} {bold(away)}\n\nGame changed! Thoughts? 👇\n\n{tag} #RedCard"
                if post_fb(msg): posted.add(key)

        # PENALTY
        if 'Penalty' in detail:
            key=f"{fid}_PEN_{pid}_{t}"
            if key not in posted:
                msg=f"🟢 {bold('PENALTY!')} {t}' | {league}\n\n{home} {gh}-{ga} {away}\n\n{e['player']['name']} - {detail}\n\nScored or missed? 👇\n\n{tag} #Penalty"
                if post_fb(msg): posted.add(key)

        # VAR / OWN GOAL
        if 'Own Goal' in detail or 'VAR' in detail:
            key=f"{fid}_VAR_{pid}_{t}"
            if key not in posted:
                msg=f"🟢 {bold('DRAMA!')} {t}' | {league}\n\n{detail}: {e['player']['name']}\n\n{bold(home)} {gh}-{ga} {bold(away)}\n\n😱 What a moment!\n\n{tag}"
                if post_fb(msg): posted.add(key)

    # HT / FT - once
    if status=='HT':
        key=f"{fid}_HT_{gh}-{ga}"
        if key not in posted:
            if post_fb(f"🟢 {bold('HALF-TIME')} | {league}\n\n{bold(home)} {gh}-{ga} {bold(away)}\n\nYour thoughts on first half? 👇\n\n{tag} #HT"): posted.add(key)
    if status=='FT':
        key=f"{fid}_FT_{gh}-{ga}"
        if key not in posted:
            if post_fb(f"🟢 {bold('FULL-TIME')} | {league}\n\n{bold(home)} {gh}-{ga} {bold(away)}\n\nRate this game 1-10! 👇\n\n{tag} #FT"): posted.add(key)

# === 2. LINEUP DROP - 1 hour before ===
try:
    today=datetime.utcnow().strftime('%Y-%m-%d')
    r=requests.get(f"{BASE}/fixtures?date={today}&timezone=Africa/Nairobi", headers=HEADERS, timeout=15).json().get('response',[])
    for f in r:
        if f['fixture']['status']['short']!='NS': continue
        fid=f['fixture']['id']
        key=f"{fid}_LINEUP"
        if key in posted: continue
        # check lineup ready
        lr=requests.get(f"{BASE}/fixtures/lineups?fixture={fid}", headers=HEADERS, timeout=10).json().get('response',[])
        if lr:
            league=f['league']['name']; home=f['teams']['home']['name']; away=f['teams']['away']['name']
            msg=f"🟢 {bold('LINEUP DROP!')} | {league}\n\n{bold(home)} vs {bold(away)}\n\nStarting XIs are OUT! Kickoff soon.\n\nWho wins? Predict lineup! 👇\n\n#Lineup #BuildUp {tag if 'tag' in locals() else '#UnfilteredScores'}"
            if post_fb(msg): posted.add(key); break # one lineup per run
except Exception as e: print(f"LINEUP ERR {e}")

# === 3. BREAKING TRANSFERS - when no live ===
if len(lives)==0:
    try:
        today=datetime.utcnow().strftime('%Y-%m-%d')
        tr=requests.get(f"{BASE}/transfers?date={today}", headers=HEADERS, timeout=15).json().get('response',[])
        if tr:
            t=tr[0]; player=t['player']['name']
            trans=t['transfers'][0] if t['transfers'] else None
            to_team=trans['teams']['in']['name'] if trans else "New Club"
            from_team=trans['teams']['out']['name'] if trans else ""
            key=f"TRANSFER_{player}_{today}"
            if key not in posted:
                msg=f"🟢 {bold('BREAKING: TRANSFER NEWS')}\n\n{bold(player)}\n{from_team} ➡️ {to_team}\n\nDone deal? Yes or No? 👇\n\n#Transfer #Breaking 🟢 #UnfilteredScores"
                if post_fb(msg): posted.add(key)
    except Exception as e: print(f"TRANSFER ERR {e}")

save_posted(posted)
print("Done V3")
