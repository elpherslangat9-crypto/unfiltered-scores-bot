import os, requests
from datetime import datetime, timezone

BRAND = "🟢 Unfiltered Scores"
TAGLINE = "No Filters, Just Football"
HASHTAGS = "#UnfilteredScores #WorldFootballToday"
FB_PAGE_ID = os.getenv("FB_PAGE_ID", "61595099671352").strip()
FB_TOKEN = (os.getenv("FB_PAGE_TOKEN") or os.getenv("FB_TOKEN") or "").strip()

LEAGUES = ["eng.1","esp.1","ita.1","ger.1","fra.1","usa.1","sau.1","ken.1","rsa.1","nga.1","egy.1","bra.1","arg.1","mex.1","uefa.champions","caf.champions","aus.1","jpn.1","ind.1","tur.1","ned.1","por.1"]

def bold(t):
    m="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    b="𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"
    try:
        return "".join(b[m.index(c)] if c in m else c for c in t)
    except:
        return t

def fb_post(msg):
    if not FB_PAGE_ID or not FB_TOKEN:
        print(f"FB SKIP - Missing Secrets. ID set:{bool(FB_PAGE_ID)} TOKEN set:{bool(FB_TOKEN)}")
        return False

    print(f"FB TRY - PageID:{FB_PAGE_ID} TokenLen:{len(FB_TOKEN)} Start:{FB_TOKEN[:20]}...")
    url=f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed"

    # Facebook needs message under 2000 chars ideally, split if too long
    if len(msg) > 8000:
        msg = msg[:7900] + "\n\n...full list on page!"

    try:
        r=requests.post(url, data={"message": msg, "access_token": FB_TOKEN}, timeout=30)
        print(f"FB {r.status_code}: {r.text[:1000]}")
        if r.status_code == 200:
            print(f"FB OK - ID:{r.json().get('id')}")
            return True
        else:
            # If token is User token, error will be (#200) or (#100)
            return False
    except Exception as e:
        print(f"FB EXCEPTION: {e}")
        return False

def espn_get(url):
    try:
        r=requests.get(url, timeout=15, headers={"User-Agent":"Mozilla/5.0"})
        return r.json() if r.status_code==200 else {}
    except: return {}

def main():
    now=datetime.now(timezone.utc)
    today = now.strftime("%Y%m%d")
    mode = os.getenv("DAILY_MODE", "morning") # morning or night
    print(f"DAILY {mode} - {today} | {BRAND}")
    print(f"DEBUG SECRETS - ID:{FB_PAGE_ID} TokenLen:{len(FB_TOKEN)}")

    games = []
    for lc in LEAGUES:
        d = espn_get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lc}/scoreboard?dates={today}")
        for ev in d.get("events", []):
            try:
                comp = ev['competitions'][0]
                home = next(c for c in comp['competitors'] if c['homeAway']=='home')
                away = next(c for c in comp['competitors'] if c['homeAway']=='away')
                h = home['team']['displayName']
                a = away['team']['displayName']
                hs = home.get('score','?')
                as_ = away.get('score','?')
                ko = datetime.fromisoformat(ev['date'].replace("Z","+00:00"))
                ko_eat = f"{(ko.hour+3)%24:02d}:{ko.minute:02d}"
                status = ev['status']['type']['state']
                league = ev.get('league',{}).get('name', lc)
                games.append((ko_eat, f"{bold(h)} vs {bold(a)} | {league} | {ko_eat} EAT | {hs}-{as_} {status}", ev))
            except: continue

    games.sort()
    if not games:
        print("No games today - posting info message")
        msg = f"{BRAND}\n{bold('No major games today')}\n━━━━━━━━━━━━━━\n{now.strftime('%A, %d %B %Y')} | {TAGLINE}\n\nCheck back tomorrow! 🌍\n\n{HASHTAGS}"
        fb_post(msg)
        return

    print(f"Found {len(games)} games across {len(LEAGUES)} leagues")

    if mode == "morning":
        msg = f"{BRAND}\n{bold(f'TODAY FIXTURES - {len(games)} GAMES WORLDWIDE 🌍')}\n━━━━━━━━━━━━━━\n{now.strftime('%A, %d %B %Y')} | {TAGLINE}\n\n"
        for _, line, _ in games[:30]:
            msg += f"⚽ {line}\n"
        if len(games) > 30:
            msg += f"\n+ {len(games)-30} more games in other leagues!\n"
        msg += f"\nLineups 1hr before KO, LIVE goals every 4 mins 🟢\n\n{HASHTAGS} #Fixtures"
    else:
        finished = [g for g in games if "post" in str(g[2]['status']['type']['state'])]
        if not finished:
            finished = games # if no FT yet, show current
        msg = f"{BRAND}\n{bold(f'TODAY RESULTS - {len(finished)} FT 🌍')}\n━━━━━━━━━━━━━━\n{now.strftime('%A, %d %B %Y')}\n\n"
        for _, line, ev in finished[:25]:
            try:
                comp = ev['competitions'][0]
                home = next(c for c in comp['competitors'] if c['homeAway']=='home')
                away = next(c for c in comp['competitors'] if c['homeAway']=='away')
                msg += f"✅ {bold(home['team']['displayName'])} {home.get('score','0')} - {away.get('score','0')} {bold(away['team']['displayName'])} | {ev.get('league',{}).get('name','')}\n"
            except: continue
        msg += f"\nFull reports on page! {TAGLINE} 🟢\n\n{HASHTAGS} #Results #FT"

    fb_post(msg)

if __name__=="__main__": main()
