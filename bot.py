# V23 FINAL FIXED - CORRECT SCORES - FOOTBALL ONLY - SHORT BADGE - FULL PHOTO - NO HIGHLIGHTS
import os, json, time, requests, re
from datetime import datetime, timezone
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import feedparser

FB_TOKEN = os.getenv("FB_TOKEN", "").strip()
FB_PAGE_ID = os.getenv("FB_PAGE_ID", "1293090263895541").strip()
print("=== V23 FINAL FIXED ===")

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
FOOTBALL_MUST_HAVE = ["football","premier","arsenal","chelsea","liverpool","man utd","manchester city","man city","tottenham","barcelona","real madrid","atletico","bayern","dortmund","psg","juventus","ac milan","inter","serie a","la liga","bundesliga","ligue 1","efl","champions league","europa","fa cup","carabao","transfer","goal","striker","midfielder","defender","manager","coach","uefa","fifa","leeds","brentford","club","league","betis"]

def is_football_news(title):
    t = title.lower()
    for bad in NON_FOOTBALL_WORDS:
        if bad in t:
            print(f"BLOCKED NON-FOOTBALL: {title}")
            return False
    for good in FOOTBALL_MUST_HAVE:
        if good in t:
            return True
    print(f"BLOCKED NOT FOOTBALL: {title}")
    return False

def fetch_json(url):
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code==200: return r.json()
    except: pass
    return None

def make_hd_image(lines):
    W,H = 1280,720
    img = Image.new("RGB", (W,H), (8,12,28))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        r = int(8 + y*0.12)
        g = int(12 + y*0.18)
        b = int(28 + y*0.25)
        draw.line([(0,y),(W,y)], fill=(r,g,b))
    try:
        b_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
        b_mid = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 38)
        b_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
        b_mini = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except: b_big=b_mid=b_small=b_mini=ImageFont.load_default()
    y=100
    for i,line in enumerate(lines[:4]):
        f = b_big if i==0 else b_mid
        fill = (255,255,255) if i<2 else (200,220,255)
        draw.text((55,y), line[:55], font=f, fill=fill)
        y+=88
        if i==0:
            draw.line([(55,y-18),(320,y-18)], fill=(0,230,90), width=4)
    # SHORT FLOATING PILL - NO BLACK STRIP
    bw, bh = 300, 38
    bx = (W - bw)//2
    by = H - 55
    draw.ellipse([bx-10, by+12, bx+bw+10, by+bh+8], fill=(0,0,0,80))
    draw.rounded_rectangle([bx, by, bx+bw, by+bh], radius=19, fill=(0,215,95))
    draw.rounded_rectangle([bx, by, bx+bw, by+bh], radius=19, outline=(255,255,255,90), width=2)
    draw.text((bx+26, by+8), "🟢 UNFILTERED SCORES", font=b_small, fill=(255,255,255))
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
            if m:
                url = m.group(1)
                if url.startswith("http"):
                    return url.replace("/480/","/1280/").replace("/320/","/1024/")
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
        x = (W - nw)//2
        y = (H - nh)//2
        canvas.paste(resized, (x,y))
        draw = ImageDraw.Draw(canvas, "RGBA")
        try:
            b_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
            b_mini = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        except: b_small=b_mini=ImageFont.load_default()
        # SHORT PILL - NO CROP DESIGN
        bw, bh = 300, 36
        bx = (W - bw)//2
        by = H - bh - 12
        draw.rounded_rectangle([bx+2, by+2, bx+bw+2, by+bh+2], radius=18, fill=(0,0,0,90))
        draw.rounded_rectangle([bx, by, bx+bw, by+bh], radius=18, fill=(0,210,85,230))
        draw.text((bx+20, by+7), "🟢 UNFILTERED SCORES", font=b_small, fill=(255,255,255))
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
    print("Scanning live ALL LEAGUES - CORRECT SCORE...")
    count=0
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for league_url in ESPN_LEAGUES:
        data=fetch_json(league_url)
        if not data: continue
        for ev in data.get("events",[]):
            try:
                ev_date = ev.get("date","")[:10]
                if ev_date != today_str:
                    continue
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
                running_h = 0
                running_a = 0
                goal_timeline = []
                for d in all_details:
                    if not isinstance(d, dict): continue
                    t = d.get("type",{})
                    t_text = t.get("text","") if isinstance(t, dict) else str(t)
                    clock = d.get("clock",{})
                    minute = clock.get("displayValue","") if isinstance(clock, dict) else ""
                    team_id = d.get("team",{}).get("id","") if isinstance(d.get("team",{}), dict) else ""
                    is_home_goal = (team_id == home.get("team",{}).get("id",""))
                    if "Own Goal" in t_text:
                        is_home_goal = not is_home_goal
                    if t_text in ["Goal","Own Goal","Penalty - Scored"]:
                        if is_home_goal: running_h += 1
                        else: running_a += 1
                        inv = safe_list(d.get("athletesInvolved",[]))
                        scorer = inv[0].get("displayName","") if inv and isinstance(inv[0], dict) else ""
                        assist = inv[1].get("displayName","") if len(inv)>1 and isinstance(inv[1], dict) else ""
                        goal_timeline.append({"id":d.get("id",""), "minute":minute, "h":running_h, "a":running_a, "scorer":scorer, "assist":assist, "type":t_text})

                if state_type=="in" or "Half" in status or "In Progress" in status:
                    key_line=f"lineup_{ev_id}"
                    if not is_posted(key_line):
                        msg=f"🔥 KICK OFF!\n{h_team} vs {a_team}\nLIVE NOW!\n\nFollow 🟢 UNFILTERED SCORES - Fastest Live!"
                        img=make_hd_image([f"{h_team} vs {a_team}", f"LIVE  {running_h}-{running_a}", "KICK OFF", "LINEUPS CONFIRMED"])
                        if post_fb(msg, img):
                            mark(key_line)
                            count+=1

                for g in goal_timeline:
                    key=f"goal_{ev_id}_{g['id']}"
                    if is_posted(key): continue
                    if state_type=="post": continue
                    goal_type = "PENALTY!" if "Penalty" in g['type'] else ("OWN GOAL!" if "Own" in g['type'] else "GOAL!")
                    assist_txt = f"\nAssist: {g['assist']}" if g['assist'] else ""
                    msg=f"⚽ {goal_type} {g['minute']}'\n{h_team} {g['h']}-{g['a']} {a_team}\nScorer: {g['scorer']}{assist_txt}\n\n🟢 UNFILTERED SCORES - Fastest!"
                    img=make_hd_image([f"{goal_type} {g['minute']}'", f"{h_team} {g['h']}-{g['a']}", a_team, g['scorer']])
                    if post_fb(msg, img):
                        mark(key)
                        count+=1
                        time.sleep(2)

                for d in all_details:
                    if not isinstance(d, dict): continue
                    t = d.get("type",{})
                    t_text = t.get("text","") if isinstance(t, dict) else ""
                    if t_text in ["Red Card","Yellow-Red Card"]:
                        key=f"red_{ev_id}_{d.get('id','')}"
                        if is_posted(key): continue
                        if state_type=="post": continue
                        inv = safe_list(d.get("athletesInvolved",[]))
                        scorer = inv[0].get("displayName","") if inv and isinstance(inv[0], dict) else ""
                        minute = d.get("clock",{}).get("displayValue","") if isinstance(d.get("clock",{}), dict) else ""
                        msg=f"🟥 RED CARD! {minute}'\n{h_team} {running_h}-{running_a} {a_team}\nPlayer: {scorer}\n\n🟢 UNFILTERED SCORES"
                        img=make_hd_image([f"RED CARD {minute}'", f"{h_team} {running_h}-{running_a}", a_team, scorer])
                        if post_fb(msg, img):
                            mark(key)
                            count+=1

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
    print("V23 START - Correct scores, football only, never miss")
    for i in range(25):
        try:
            process_live()
            if i%2==0:
                process_news()
        except Exception as e:
            print(f"MAIN ERR {e}")
        if time.time()-start>550: break
        time.sleep(20)
    print("DONE V23")
