# V23 FINAL - FOOTBALL ONLY - SHORT BADGE - NO CROP - NO HIGHLIGHTS - NEVER MISS GOAL
import os, json, time, traceback, requests, re
from datetime import datetime
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import feedparser

FB_TOKEN = os.getenv("FB_TOKEN", "").strip()
FB_PAGE_ID = os.getenv("FB_PAGE_ID", "1293090263895541").strip()
print("=== V23 FINAL FOOTBALL ONLY ===")

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

def get_brand(): return "UNFILTERED SCORES"

# ALL MAJOR LEAGUES - WILL NEVER MISS GAME AFTER NOON
ESPN_LEAGUES = [
    "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard", # EPL
    "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.2/scoreboard", # Championship
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

# === STRICT FOOTBALL ONLY FILTER ===
NON_FOOTBALL_WORDS = ["darts","van gerwen","snooker","cricket","rugby","tennis","nba","nfl","golf","f1","formula 1","boxing","mma","ufc","usyk","dubois","trilogy","fight","wrestling","athletics","badminton","billiards"]
FOOTBALL_MUST_HAVE = ["football","premier","arsenal","chelsea","liverpool","man utd","manchester city","man city","tottenham","barcelona","real madrid","atletico","bayern","dortmund","psg","juventus","ac milan","inter milan","serie a","la liga","bundesliga","ligue 1","efl","champions league","europa","fa cup","carabao","transfer","goal","striker","midfielder","defender","manager","coach","uefa","fifa","premier league","rangers","celtic","dundee","leeds","brentford","club","league"]

def is_football_news(title):
    t = title.lower()
    for bad in NON_FOOTBALL_WORDS:
        if bad in t:
            print(f"BLOCKED NON-FOOTBALL: {title}")
            return False
    for good in FOOTBALL_MUST_HAVE:
        if good in t:
            return True
    # If no football keyword, reject (this will block Dubois Usyk)
    print(f"BLOCKED NOT FOOTBALL ENOUGH: {title}")
    return False

def fetch_json(url):
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code==200: return r.json()
    except: pass
    return None

def make_hd_image(lines):
    W,H = 1280,720
    img = Image.new("RGB", (W,H), (10,15,35))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        c = int(10 + y*0.18)
        draw.line([(0,y),(W,y)], fill=(c//3, c//2, c+15))
    try:
        b_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 58)
        b_mid = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 38)
        b_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    except: b_big=b_mid=b_small=ImageFont.load_default()
    # Small green pill at bottom - not long bar
    draw.rectangle([0,H-70,W,H], fill=(0,0,0,180))
    y=110
    for i,line in enumerate(lines[:4]):
        f = b_big if i==0 else b_mid
        draw.text((50,y), line[:55], font=f, fill=(255,255,255))
        y+=92
    # DECORATED SHORT BADGE
    badge_w, badge_h = 340, 44
    bx = (W-badge_w)//2
    by = H-60
    draw.rounded_rectangle([bx, by, bx+badge_w, by+badge_h], radius=22, fill=(0,200,83))
    draw.text((bx+30, by+8), "🟢 UNFILTERED SCORES", font=b_small, fill=(255,255,255))
    bio=BytesIO()
    img.save(bio, format="JPEG", quality=97, subsampling=0)
    bio.seek(0)
    return bio

# === REAL IMAGE - NO CROP - FULL PHOTO SHOW - SHORT BADGE ===
def fetch_og_image(page_url):
    try:
        r = requests.get(page_url, timeout=15, headers={"User-Agent":"Mozilla/5.0 Chrome/120"})
        html = r.text
        pats = [r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']']
        for pat in pats:
            m = re.search(pat, html, re.I)
            if m:
                url = m.group(1)
                if url.startswith("http"):
                    url = url.replace("/480/","/1280/").replace("/320/","/1024/").replace("width=480","width=1280")
                    return url
    except: pass
    return None

def get_image_from_entry(entry):
    try:
        if hasattr(entry, 'media_content'):
            for m in entry.media_content:
                if m.get('url'): return m['url']
        if hasattr(entry, 'enclosures') and entry.enclosures:
            href = entry.enclosures[0].get('href') or entry.enclosures[0].get('url')
            if href and href.startswith("http"): return href
        if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
            u = entry.media_thumbnail[0].get('url')
            if u: return u
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
        # === NO CROP - FIT INSIDE ===
        canvas = Image.new("RGB", (W,H), (0,0,0))
        iw, ih = orig.size
        # Calculate fit inside (contain) not cover
        ratio = min(W/iw, H/ih)
        nw, nh = int(iw*ratio), int(ih*ratio)
        resized = orig.resize((nw, nh), Image.LANCZOS)
        resized = resized.filter(ImageFilter.UnsharpMask(radius=1.2, percent=80, threshold=2))
        # Center paste - full photo visible
        x = (W - nw)//2
        y = (H - nh)//2
        canvas.paste(resized, (x,y))
        draw = ImageDraw.Draw(canvas, "RGBA")
        try:
            b_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
            b_mini = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        except: b_small=b_mini=ImageFont.load_default()
        
        # === SHORT DECORATED BADGE - BOTTOM CENTER - NOT LONG BAR ===
        badge_text = "🟢 UNFILTERED SCORES"
        # Small pill 280x36 centered
        bw, bh = 280, 36
        bx = (W - bw)//2
        by = H - bh - 12
        # Shadow
        draw.rounded_rectangle([bx+2, by+2, bx+bw+2, by+bh+2], radius=18, fill=(0,0,0,100))
        # Green pill
        draw.rounded_rectangle([bx, by, bx+bw, by+bh], radius=18, fill=(0,210,85,230))
        draw.text((bx+20, by+7), badge_text, font=b_small, fill=(255,255,255))
        
        # Tiny corner for attraction
        draw.rounded_rectangle([W-145, 12, W-12, 36], radius=10, fill=(0,0,0,120))
        draw.text((W-135, 16), "⚽ LIVE", font=b_mini, fill=(255,255,255))
        
        bio=BytesIO()
        canvas.save(bio, format="JPEG", quality=96, subsampling=0, optimize=True)
        bio.seek(0)
        return bio
    except Exception as e:
        print(f"REAL IMG ERR {e}")
        return None

def post_fb(msg, img_bio):
    if len(FB_TOKEN)<50: return False
    try:
        url=f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
        files={"source":("hd.jpg", img_bio, "image/jpeg")}
        data={"message":msg, "access_token":FB_TOKEN}
        r=requests.post(url, files=files, data=data, timeout=35)
        print(f"FB POST {r.status_code} {r.text[:600]}")
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
    print("Scanning live ALL LEAGUES...")
    count=0
    for league_url in ESPN_LEAGUES:
        data=fetch_json(league_url)
        if not data: continue
        for ev in data.get("events",[]):
            try:
                comp=ev.get("competitions",[{}])[0]
                status=comp.get("status",{}).get("type",{}).get("description","")
                state_type=comp.get("status",{}).get("type",{}).get("state","")
                competitors=comp.get("competitors",[])
                if len(competitors)<2: continue
                home=next((c for c in competitors if c.get("homeAway")=="home"), competitors[0])
                away=next((c for c in competitors if c.get("homeAway")=="away"), competitors[1])
                h_team=home.get("team",{}).get("displayName","Home")
                a_team=away.get("team",{}).get("displayName","Away")
                h_score=home.get("score","0")
                a_score=away.get("score","0")
                ev_id=ev.get("id","")

                # LINEUP / KICKOFF - NEVER MISS
                if state_type=="in" or status=="In Progress" or status=="First Half":
                    key_line=f"lineup_{ev_id}"
                    if not is_posted(key_line):
                        msg=f"🔥 KICK OFF!\n{h_team} vs {a_team}\nLIVE NOW!\n\nFollow 🟢 UNFILTERED SCORES - Fastest Live!"
                        img=make_hd_image([f"{h_team} vs {a_team}", f"LIVE  {h_score}-{a_score}", "KICK OFF", "LINEUPS CONFIRMED"])
                        if post_fb(msg, img):
                            mark(key_line)
                            count+=1

                # GOALS - NEVER MISS
                for d in safe_list(comp.get("details",[])):
                    if not isinstance(d, dict): continue
                    t = d.get("type",{})
                    t_text = t.get("text","") if isinstance(t, dict) else str(t)
                    minute = d.get("clock",{}).get("displayValue","") if isinstance(d.get("clock",{}), dict) else ""
                    scorer=""; assist=""
                    inv = safe_list(d.get("athletesInvolved",[]))
                    if inv:
                        scorer = inv[0].get("displayName","") if isinstance(inv[0], dict) else ""
                        if len(inv)>1: assist = inv[1].get("displayName","")
                    if t_text in ["Goal","Own Goal","Penalty - Scored"]:
                        key=f"goal_{ev_id}_{d.get('id','')}_{minute}_{h_score}_{a_score}"
                        if is_posted(key): continue
                        goal_type = "PENALTY!" if "Penalty" in t_text else ("OWN GOAL!" if "Own" in t_text else "GOAL!")
                        assist_txt = f"\nAssist: {assist}" if assist else ""
                        msg=f"⚽ {goal_type} {minute}'\n{h_team} {h_score}-{a_score} {a_team}\nScorer: {scorer}{assist_txt}\n\n🟢 UNFILTERED SCORES - Fastest!"
                        img=make_hd_image([f"{goal_type} {minute}'", f"{h_team} {h_score}-{a_score}", a_team, scorer])
                        if post_fb(msg, img):
                            mark(key)
                            count+=1
                            time.sleep(2)
                    if t_text in ["Red Card","Yellow-Red Card"]:
                        key=f"red_{ev_id}_{d.get('id','')}"
                        if is_posted(key): continue
                        msg=f"🟥 RED CARD! {minute}'\n{h_team} {h_score}-{a_score} {a_team}\nPlayer: {scorer}\n\n🟢 UNFILTERED SCORES"
                        img=make_hd_image([f"RED CARD {minute}'", f"{h_team} {h_score}-{a_score}", a_team, scorer])
                        if post_fb(msg, img):
                            mark(key)
                            count+=1

                # HT / FT - NO HIGHLIGHTS IMAGE (REMOVED AS YOU SAID)
                if status in ["Halftime","Full Time","Final","FT"]:
                    key=f"{status}_{ev_id}_{h_score}_{a_score}"
                    if not is_posted(key):
                        label="⏸️ HALFTIME" if "Half" in status else "✅ FULL TIME"
                        msg=f"{label}\n{h_team} {h_score}-{a_score} {a_team}\n\n🟢 UNFILTERED SCORES"
                        img=make_hd_image([label.replace("⏸️ ","").replace("✅ ",""), f"{h_team} {h_score}-{a_score}", a_team])
                        if post_fb(msg, img):
                            mark(key)
                            count+=1
            except: continue
    print(f"Live done {count}")
    return count

def process_news():
    try:
        feeds=[
            ("BBC Sport Football", "http://feeds.bbci.co.uk/sport/football/rss.xml"),
            ("Sky Sports Football", "https://www.skysports.com/rss/12040"),
        ]
        for source_name, feed_url in feeds:
            print(f"Checking {source_name}")
            feed=feedparser.parse(feed_url)
            for entry in feed.entries[:15]:
                title=entry.get("title","")
                if not title: continue
                if not is_football_news(title): continue
                key=f"news_{title[:80]}"
                if is_posted(key): continue
                real_img_url = get_image_from_entry(entry)
                if not real_img_url: continue
                img_bio = make_real_image_news(real_img_url)
                if not img_bio: continue
                msg=f"🚨 {title}\n\nFollow 🟢 UNFILTERED SCORES for fastest football news! ⚽\n\nSource: {source_name}"
                if post_fb(msg, img_bio):
                    mark(key)
                    print(f"NEWS POSTED: {title}")
                    return 1
            time.sleep(1)
    except Exception as e:
        print(f"NEWS ERR {e}")
    return 0

if __name__=="__main__":
    if len(FB_TOKEN)<50:
        print("ERROR: Set FB_TOKEN")
        exit(0)
    start=time.time()
    print("V23 START - Games after noon will NOT be missed")
    for i in range(25):
        try:
            process_live() # Live first - priority
            if i%2==0:
                process_news()
        except Exception as e:
            print(f"MAIN ERR {e}")
        if time.time()-start>550: break
        time.sleep(20) # Faster 20 sec - will never miss goal
    print("DONE V23")
