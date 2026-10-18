# V23 FINAL FIXED - REAL LINEUPS IN PHOTO - CORRECT OWN GOAL 1-0 - BIG BADGE - FOOTBALL ONLY
import os, json, time, requests, re
from datetime import datetime, timezone
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import feedparser

FB_TOKEN = os.getenv("FB_TOKEN", "").strip()
FB_PAGE_ID = os.getenv("FB_PAGE_ID", "1293090263895541").strip()
print("=== V23 FINAL FIXED - LINEUPS EDITION ===")

STATE_FILE = "state.json"
def load_state():
    try:
        with open(STATE_FILE, "r") as f: return json.load(f)
    except: return {"posted": []}
def save_state(s):
    try:
        with open(STATE_FILE, "w") as f: json.dump(s, f)
    except: pass
state = load_state()

def safe_list(x):
    if isinstance(x, list): return x
    if isinstance(x, dict): return [x]
    if not x: return []
    return [x]

ESPN_LEAGUES = [
    "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard",
    "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.2/scoreboard",
    "https://site.api.espn.com/apis/site/v2/sports/soccer/esp.1/scoreboard",
    "https://site.api.espn.com/apis/site/v2/sports/soccer/ita.1/scoreboard",
    "https://site.api.espn.com/apis/site/v2/sports/soccer/ger.1/scoreboard",
    "https://site.api.espn.com/apis/site/v2/sports/soccer/fra.1/scoreboard",
    "https://site.api.espn.com/apis/site/v2/sports/soccer/ned.1/scoreboard",
    "https://site.api.espn.com/apis/site/v2/sports/soccer/por.1/scoreboard",
    "https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/scoreboard",
    "https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.europa/scoreboard",
    "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.worldq/scoreboard",
]

NON_FOOTBALL_WORDS = ["darts","van gerwen","snooker","cricket","rugby","tennis","nba","nfl","golf","f1","formula 1","boxing","mma","ufc","usyk","dubois","trilogy","fight","wrestling","athletics"]
FOOTBALL_MUST_HAVE = ["football","premier","arsenal","chelsea","liverpool","man utd","manchester city","man city","tottenham","barcelona","real madrid","atletico","bayern","dortmund","psg","juventus","ac milan","inter","serie a","la liga","bundesliga","ligue 1","efl","champions league","europa","fa cup","carabao","transfer","goal","striker","midfielder","defender","manager","coach","uefa","fifa","brighton","palace","betis"]

def is_football_news(title):
    t = title.lower()
    for bad in NON_FOOTBALL_WORDS:
        if bad in t: return False
    for good in FOOTBALL_MUST_HAVE:
        if good in t: return True
    print(f"BLOCKED NOT FOOTBALL: {title}")
    return False

def fetch_json(url):
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code==200: return r.json()
    except: pass
    return None

# ===== GOAL / RED / HT / FT IMAGE - BIG BADGE =====
def make_hd_image(lines):
    W,H = 1280,720
    img = Image.new("RGB", (W,H), (10,20,45))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        r = int(10 + y*0.08)
        g = int(20 + y*0.15)
        b = int(45 + y*0.28)
        draw.line([(0,y),(W,y)], fill=(r,g,b))
    try:
        b_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
        b_mid = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 38)
        b_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    except: b_big=b_mid=b_small=ImageFont.load_default()
    y=100
    for i,line in enumerate(lines[:4]):
        f = b_big if i==0 else b_mid
        fill = (255,255,255) if i<2 else (210,225,255)
        draw.text((55,y), line[:58], font=f, fill=fill)
        y+=92
        if i==0:
            draw.line([(55,y-20),(340,y-20)], fill=(0,230,90), width=5)
    # BIG DECORATED BADGE - VISIBLE
    bw, bh = 420, 52
    bx = (W - bw)//2
    by = H - 72
    draw.rounded_rectangle([bx, by+6, bx+bw, by+bh+6], radius=26, fill=(0,0,0,120))
    draw.rounded_rectangle([bx, by, bx+bw, by+bh], radius=26, fill=(0,218,92))
    draw.rounded_rectangle([bx, by, bx+bw, by+bh], radius=26, outline=(255,255,255,180), width=3)
    draw.text((bx+42, by+11), "🟢 UNFILTERED SCORES", font=b_small, fill=(255,255,255))
    bio=BytesIO()
    img.save(bio, format="JPEG", quality=97, subsampling=0)
    bio.seek(0)
    return bio

# ===== REAL LINEUPS IMAGE - BOTH TEAMS XI IN PHOTO =====
def fetch_real_lineups(event_id):
    for league_url in ESPN_LEAGUES:
        try:
            league_code = league_url.split("/soccer/")[1].split("/scoreboard")[0]
            summary_url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/summary?event={event_id}"
            data = fetch_json(summary_url)
            if not data: continue
            # Try rosters
            rosters = data.get("rosters", [])
            if len(rosters) >= 2:
                home_xi = []
                away_xi = []
                for idx, ros in enumerate(rosters[:2]):
                    athletes = ros.get("roster", [])[:11]
                    names = []
                    for a in athletes:
                        if isinstance(a, dict):
                            name = a.get("athlete",{}).get("displayName","") or a.get("displayName","")
                            pos = a.get("position",{}).get("abbreviation","") or a.get("position","")
                            if name: names.append(f"{name} ({pos})" if pos else name)
                    if idx==0: home_xi = names
                    else: away_xi = names
                if home_xi and away_xi and len(home_xi)>=7:
                    return home_xi, away_xi
        except: continue
    return None, None

def make_lineup_image(h_team, a_team, h_xi, a_xi):
    W,H = 1280,720
    img = Image.new("RGB", (W,H), (8,14,35))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        draw.line([(0,y),(W,y)], fill=(int(8+y*0.1), int(14+y*0.15), int(35+y*0.22)))
    try:
        b_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
        b_mid = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
        b_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        b_tiny = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
    except: b_big=b_mid=b_small=b_tiny=ImageFont.load_default()
    
    draw.text((30,16), f"{h_team} vs {a_team}", font=b_big, fill=(255,255,255))
    draw.line([(30,58),(520,58)], fill=(0,230,90), width=4)
    draw.text((30,68), "STARTING XI - KICK OFF", font=b_tiny, fill=(0,230,90))
    
    # Home box
    y_h = 102
    draw.rounded_rectangle([18, y_h-8, 625, H-78], radius=14, fill=(255,255,255,18))
    draw.text((38, y_h), h_team[:30].upper(), font=b_mid, fill=(255,230,0))
    y_h+=30
    for i,name in enumerate(h_xi[:11]):
        draw.text((38, y_h), f"{i+1}. {name}", font=b_small, fill=(225,235,255))
        y_h+=42
    
    # Away box
    y_a = 102
    draw.rounded_rectangle([645, y_a-8, 1260, H-78], radius=14, fill=(255,255,255,18))
    draw.text((665, y_a), a_team[:30].upper(), font=b_mid, fill=(0,220,255))
    y_a+=30
    for i,name in enumerate(a_xi[:11]):
        draw.text((665, y_a), f"{i+1}. {name}", font=b_small, fill=(225,235,255))
        y_a+=42
    
    # Big badge
    bw, bh = 420, 52
    bx = (W - bw)//2
    by = H - 66
    draw.rounded_rectangle([bx, by, bx+bw, by+bh], radius=26, fill=(0,218,92))
    draw.rounded_rectangle([bx, by, bx+bw, by+bh], radius=26, outline=(255,255,255,180), width=3)
    draw.text((bx+42, by+11), "🟢 UNFILTERED SCORES", font=b_mid, fill=(255,255,255))
    
    bio=BytesIO()
    img.save(bio, format="JPEG", quality=97, subsampling=0)
    bio.seek(0)
    return bio

def fetch_og_image(page_url):
    try:
        r = requests.get(page_url, timeout=15, headers={"User-Agent":"Mozilla/5.0 Chrome/120"})
        html = r.text
        pats = [r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']']
        for pat in pats:
            m = re.search(pat, html, re.I)
            if m and m.group(1).startswith("http"):
                return m.group(1)
    except: pass
    return None

def get_image_from_entry(entry):
    try:
        link = entry.get("link","")
        if link:
            og = fetch_og_image(link)
            if og: return og
    except: pass
    return None

def make_real_image_news(real_img_url):
    try:
        r = requests.get(real_img_url, timeout=20, headers={"User-Agent":"Mozilla/5.0 Chrome/120"})
        if r.status_code != 200: return None
        orig = Image.open(BytesIO(r.content)).convert("RGB")
        W,H = 1280,720
        canvas = Image.new("RGB", (W,H), (0,0,0))
        iw, ih = orig.size
        ratio = min(W/iw, H/ih)
        nw, nh = int(iw*ratio), int(ih*ratio)
        resized = orig.resize((nw, nh), Image.LANCZOS)
        resized = resized.filter(ImageFilter.UnsharpMask(radius=1.2, percent=80, threshold=2))
        canvas.paste(resized, ((W-nw)//2,(H-nh)//2))
        draw = ImageDraw.Draw(canvas, "RGBA")
        try:
            b_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
        except: b_small=ImageFont.load_default()
        bw, bh = 400, 48
        bx = (W - bw)//2
        by = H - 70
        draw.rounded_rectangle([bx, by, bx+bw, by+bh], radius=24, fill=(0,210,85,235))
        draw.rounded_rectangle([bx, by, bx+bw, by+bh], radius=24, outline=(255,255,255,160), width=2)
        draw.text((bx+32, by+10), "🟢 UNFILTERED SCORES", font=b_small, fill=(255,255,255))
        bio=BytesIO()
        canvas.save(bio, format="JPEG", quality=96, subsampling=0)
        bio.seek(0)
        return bio
    except: return None

def post_fb(msg, img_bio):
    if len(FB_TOKEN)<50: return False
    try:
        url=f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
        files={"source":("hd.jpg", img_bio, "image/jpeg")}
        data={"message":msg, "access_token":FB_TOKEN}
        r=requests.post(url, files=files, data=data, timeout=35)
        print(f"FB POST {r.status_code} {r.text[:500]}")
        return r.status_code==200
    except Exception as e:
        print(f"FB ERR {e}")
        return False

def is_posted(k): return k in state.get("posted",[])
def mark(k):
    p=state.get("posted",[])
    p.append(k)
    state["posted"]=p[-1000:]
    save_state(state)

def process_live():
    print("Scanning live - CORRECT OG & LINEUPS...")
    count=0
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for league_url in ESPN_LEAGUES:
        data=fetch_json(league_url)
        if not data: continue
        for ev in data.get("events",[]):
            try:
                ev_date = ev.get("date","")[:10]
                if ev_date != today_str: continue
                comp=ev.get("competitions",[{}])[0]
                status=comp.get("status",{}).get("type",{}).get("description","")
                state_type=comp.get("status",{}).get("type",{}).get("state","")
                competitors=comp.get("competitors",[])
                if len(competitors)<2: continue
                home=next((c for c in competitors if c.get("homeAway")=="home"), competitors[0])
                away=next((c for c in competitors if c.get("homeAway")=="away"), competitors[1])
                h_team=home.get("team",{}).get("displayName","Home")
                a_team=away.get("team",{}).get("displayName","Away")
                ev_id=ev.get("id","")
                all_details = safe_list(comp.get("details",[]))
                running_h=0
                running_a=0
                timeline=[]
                for d in all_details:
                    if not isinstance(d, dict): continue
                    t = d.get("type",{})
                    t_text = t.get("text","") if isinstance(t, dict) else ""
                    clock = d.get("clock",{})
                    minute_raw = clock.get("displayValue","") if isinstance(clock, dict) else ""
                    minute = minute_raw.replace("'", "").replace('"','').strip()
                    team_id = d.get("team",{}).get("id","") if isinstance(d.get("team",{}), dict) else ""
                    # FIXED: For own goal, team_id is already the team that GETS the goal (Brighton), don't invert
                    is_home_goal = (team_id == home.get("team",{}).get("id",""))
                    if t_text in ["Goal","Own Goal","Penalty - Scored"]:
                        if is_home_goal: running_h+=1
                        else: running_a+=1
                        inv = safe_list(d.get("athletesInvolved",[]))
                        scorer = inv[0].get("displayName","") if inv and isinstance(inv[0], dict) else ""
                        assist = inv[1].get("displayName","") if len(inv)>1 and isinstance(inv[1], dict) else ""
                        timeline.append({"id":d.get("id",""), "minute":minute, "h":running_h, "a":running_a, "scorer":scorer, "assist":assist, "type":t_text})

                # KICK OFF WITH REAL LINEUPS PHOTO
                if state_type=="in" or "Half" in status or "In Progress" in status:
                    key_line=f"lineup_{ev_id}"
                    if not is_posted(key_line):
                        h_xi, a_xi = fetch_real_lineups(ev_id)
                        if h_xi and a_xi:
                            img = make_lineup_image(h_team, a_team, h_xi, a_xi)
                            msg=f"🔥 KICK OFF!\n{h_team} vs {a_team}\n\nLINEUPS:\n{h_team}: {', '.join([n.split(' (')[0] for n in h_xi[:11]])}\n\n{a_team}: {', '.join([n.split(' (')[0] for n in a_xi[:11]])}\n\n🟢 UNFILTERED SCORES"
                        else:
                            img=make_hd_image([f"{h_team} vs {a_team}", f"LIVE  {running_h}-{running_a}", "KICK OFF", "LINEUPS CONFIRMED"])
                            msg=f"🔥 KICK OFF!\n{h_team} vs {a_team}\nLIVE NOW!\n\n🟢 UNFILTERED SCORES - Fastest Live!"
                        if post_fb(msg, img):
                            mark(key_line)
                            count+=1

                # GOALS WITH CORRECT OG LOGIC
                for g in timeline:
                    key=f"goal_{ev_id}_{g['id']}"
                    if is_posted(key): continue
                    if state_type=="post": continue
                    if "Own Goal" in g['type']:
                        msg=f"⚽ OWN GOAL! {g['minute']}'\n{h_team} {g['h']}-{g['a']} {a_team}\nBy {g['scorer']} (OG)\n\n🟢 UNFILTERED SCORES"
                        img=make_hd_image([f"OWN GOAL! {g['minute']}'", f"{h_team} {g['h']}-{g['a']}", a_team, f"{g['scorer']} OG"])
                    else:
                        goal_type = "PENALTY!" if "Penalty" in g['type'] else "GOAL!"
                        assist_txt = f"\nAssist: {g['assist']}" if g['assist'] else ""
                        msg=f"⚽ {goal_type} {g['minute']}'\n{h_team} {g['h']}-{g['a']} {a_team}\nScorer: {g['scorer']}{assist_txt}\n\n🟢 UNFILTERED SCORES"
                        img=make_hd_image([f"{goal_type} {g['minute']}'", f"{h_team} {g['h']}-{g['a']}", a_team, g['scorer']])
                    if post_fb(msg, img):
                        mark(key)
                        count+=1
                        time.sleep(2)

                if status in ["Halftime","Full Time","Final","FT"]:
                    key=f"{status}_{ev_id}_{running_h}_{running_a}"
                    if not is_posted(key):
                        label="⏸️ HALFTIME" if "Half" in status else "✅ FULL TIME"
                        msg=f"{label}\n{h_team} {running_h}-{running_a} {a_team}\n\n🟢 UNFILTERED SCORES"
                        img=make_hd_image([label.replace("⏸️ ","").replace("✅ ",""), f"{h_team} {running_h}-{running_a}", a_team])
                        if post_fb(msg, img):
                            mark(key)
                            count+=1
            except Exception as e:
                print(f"EV ERR {e}")
                continue
    print(f"Live done {count}")
    return count

def process_news():
    try:
        feeds=[("BBC Football","http://feeds.bbci.co.uk/sport/football/rss.xml"),("Sky Football","https://www.skysports.com/rss/12040")]
        for source_name, feed_url in feeds:
            feed=feedparser.parse(feed_url)
            for entry in feed.entries[:12]:
                title=entry.get("title","")
                if not title or not is_football_news(title): continue
                key=f"news_{title[:80]}"
                if is_posted(key): continue
                real_img_url = get_image_from_entry(entry)
                if not real_img_url: continue
                img_bio = make_real_image_news(real_img_url)
                if not img_bio: continue
                msg=f"🚨 {title}\n\nFollow 🟢 UNFILTERED SCORES for fastest football news! ⚽\n\nSource: {source_name}"
                if post_fb(msg, img_bio):
                    mark(key)
                    return 1
    except Exception as e:
        print(f"NEWS ERR {e}")
    return 0

if __name__=="__main__":
    if len(FB_TOKEN)<50:
        print("ERROR: Set FB_TOKEN")
        exit(0)
    start=time.time()
    print("V23 START - Lineups + Correct OG 1-0")
    for i in range(28):
        try:
            process_live()
            if i%3==0: process_news()
        except Exception as e:
            print(f"MAIN ERR {e}")
        if time.time()-start>550: break
        time.sleep(20)
    print("DONE V23")
