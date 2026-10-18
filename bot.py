# V24 SHORT FIXED - CORRECT SCORE + LINEUP+BENCH SEPARATE KICKOFF
import os, json, time, requests, re
from datetime import datetime, timezone
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import feedparser

FB_TOKEN = os.getenv("FB_TOKEN", "").strip()
FB_PAGE_ID = os.getenv("FB_PAGE_ID", "1293090263895541").strip()
print("=== V24 SHORT FIXED ===")

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
FOOTBALL_MUST_HAVE = ["football","premier","arsenal","chelsea","liverpool","man utd","manchester city","man city","tottenham","barcelona","real madrid","atletico","bayern","dortmund","psg","juventus","ac milan","inter","serie a","la liga","bundesliga","ligue 1","efl","champions league","europa","fa cup","carabao","transfer","goal","striker","midfielder","defender","manager","coach","uefa","fifa","leeds","brentford","club","league","betis","como","fiorentina"]

def is_football_news(title):
    t = title.lower()
    for bad in NON_FOOTBALL_WORDS:
        if bad in t: return False
    for good in FOOTBALL_MUST_HAVE:
        if good in t: return True
    return False

def fetch_json(url):
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code==200: return r.json()
    except: pass
    return None

def get_correct_score(competitors):
    try:
        h = next((c for c in competitors if c.get("homeAway")=="home"), competitors[0])
        a = next((c for c in competitors if c.get("homeAway")=="away"), competitors[1])
        return int(h.get("score") or 0), int(a.get("score") or 0)
    except: return 0,0

def make_hd_image(lines):
    W,H = 1280,720
    img = Image.new("RGB", (W,H), (8,12,28))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        draw.line([(0,y),(W,y)], fill=(int(8+y*0.12), int(12+y*0.18), int(28+y*0.25)))
    try:
        b_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
        b_mid = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 38)
        b_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
    except: b_big=b_mid=b_small=ImageFont.load_default()
    y=100
    for i,line in enumerate(lines[:4]):
        f = b_big if i==0 else b_mid
        draw.text((55,y), line[:55], font=f, fill=(255,255,255))
        y+=88
        if i==0: draw.line([(55,y-18),(320,y-18)], fill=(0,230,90), width=4)
    bw,bh=300,38; bx=(W-bw)//2; by=H-55
    draw.rounded_rectangle([bx, by, bx+bw, by+bh], radius=19, fill=(0,215,95))
    draw.text((bx+26, by+8), "🟢 UNFILTERED SCORES", font=b_small, fill=(255,255,255))
    bio=BytesIO(); img.save(bio, format="JPEG", quality=97); bio.seek(0); return bio

def fetch_real_lineups(event_id):
    for league_url in ESPN_LEAGUES:
        try:
            code = league_url.split("/soccer/")[1].split("/scoreboard")[0]
            data = fetch_json(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/summary?event={event_id}")
            if not data: continue
            rosters = data.get("rosters", [])
            if len(rosters)>=2:
                res={"home":{"xi":[],"bench":[]},"away":{"xi":[],"bench":[]}}
                for idx, ros in enumerate(rosters[:2]):
                    key="home" if idx==0 else "away"
                    xi=[]; bench=[]
                    for a in ros.get("roster",[]):
                        if not isinstance(a,dict): continue
                        ath=a.get("athlete",{}); name=ath.get("displayName","") or a.get("displayName","")
                        jersey=str(a.get("jersey","") or ""); pos=a.get("position",{}).get("abbreviation","")
                        disp=f"{jersey} {name} ({pos})".strip() if name else ""
                        if a.get("starter"): xi.append(disp or name)
                        else: bench.append(name)
                    if not xi:
                        xi=[r.get("athlete",{}).get("displayName","") for r in ros.get("roster",[])[:11]]
                        bench=[r.get("athlete",{}).get("displayName","") for r in ros.get("roster",[])[11:18]]
                    res[key]["xi"]=xi[:11]; res[key]["bench"]=bench[:7]
                if res["home"]["xi"] and len(res["home"]["xi"])>=7: return res
        except: continue
    return None

def make_lineup_image(h_team, a_team, ld):
    W,H=1280,850
    img=Image.new("RGB",(W,H),(8,14,35))
    draw=ImageDraw.Draw(img)
    for y in range(H): draw.line([(0,y),(W,y)], fill=(int(8+y*0.1), int(14+y*0.15), int(35+y*0.22)))
    try:
        b_big=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",32)
        b_mid=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",20)
        b_small=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",17)
        b_tiny=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",16)
    except: b_big=b_mid=b_small=b_tiny=ImageFont.load_default()
    draw.text((30,16), f"{h_team} vs {a_team}", font=b_big, fill=(255,255,255))
    draw.text((30,62), "★ CONFIRMED LINEUPS + BENCH", font=b_tiny, fill=(0,230,90))
    def card(x, team, d):
        y0=98
        draw.rounded_rectangle([x, y0-6, x+607, H-70], radius=14, fill=(255,255,255))
        draw.rounded_rectangle([x, y0-6, x+607, y0+28], radius=14, fill=(0,200,85))
        draw.rectangle([x, y0+14, x+607, y0+28], fill=(0,200,85))
        draw.text((x+14, y0), team.upper()[:26], font=b_mid, fill=(255,255,255))
        y=y0+36
        for i,pl in enumerate(d["xi"][:11]):
            draw.ellipse([x+8, y-2, x+38, y+18], fill=(0,185,75))
            draw.text((x+14, y), str(i+1), font=b_small, fill=(255,255,255))
            draw.text((x+46, y), pl[:28], font=b_small, fill=(10,10,10))
            y+=34
        draw.line([(x+8, y+2),(x+597, y+2)], fill=(0,200,85), width=2)
        draw.text((x+12, y+6), "BENCH:", font=b_tiny, fill=(0,150,60)); y+=26
        for b in d["bench"][:6]:
            draw.text((x+12, y), f"• {b[:26]}", font=b_tiny, fill=(30,30,30)); y+=20
    card(18, h_team, ld["home"]); card(645, a_team, ld["away"])
    bw,bh=360,42; bx=(W-bw)//2; by=H-60
    draw.rounded_rectangle([bx, by, bx+bw, by+bh], radius=21, fill=(0,218,92))
    draw.text((bx+22, by+8), "🟢 UNFILTERED SCORES", font=b_mid, fill=(255,255,255))
    bio=BytesIO(); img.save(bio, format="JPEG", quality=96); bio.seek(0); return bio

def make_kickoff_image(h_team, a_team):
    W,H=1280,720
    img=Image.new("RGB",(W,H),(8,14,35))
    draw=ImageDraw.Draw(img)
    for y in range(H): draw.line([(0,y),(W,y)], fill=(int(8+y*0.12), int(14+y*0.18), int(35+y*0.25)))
    try:
        b_big=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",60)
        b_mid=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",32)
        b_small=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",22)
    except: b_big=b_mid=b_small=ImageFont.load_default()
    draw.text((80,180), "⚽ KICK OFF!", font=b_big, fill=(0,230,90))
    draw.text((80,260), h_team[:30], font=b_mid, fill=(255,255,255))
    draw.text((80,305), "VS", font=b_small, fill=(0,230,90))
    draw.text((80,335), a_team[:30], font=b_mid, fill=(255,255,255))
    draw.text((80,395), "LIVE NOW - Predict? 👇", font=b_small, fill=(255,255,100))
    bw,bh=360,42; bx=(W-bw)//2; by=H-60
    draw.rounded_rectangle([bx, by, bx+bw, by+bh], radius=21, fill=(0,218,92))
    draw.text((bx+22, by+8), "🟢 UNFILTERED SCORES", font=b_mid, fill=(255,255,255))
    bio=BytesIO(); img.save(bio, format="JPEG", quality=96); bio.seek(0); return bio

def fetch_og_image(page_url):
    try:
        r=requests.get(page_url, timeout=15, headers={"User-Agent":"Mozilla/5.0 Chrome/120"})
        m=re.search(r'property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', r.text, re.I)
        if m: return m.group(1).replace("/480/","/1280/")
    except: pass
    return None

def get_image_from_entry(entry):
    try:
        if hasattr(entry,'media_content'):
            for m in entry.media_content:
                if m.get('url'): return m['url']
        if hasattr(entry,'enclosures') and entry.enclosures:
            href=entry.enclosures[0].get('href')
            if href and href.startswith("http"): return href
        link=entry.get("link","")
        if link: return fetch_og_image(link)
    except: pass
    return None

def make_real_image_news(real_img_url):
    try:
        r=requests.get(real_img_url, timeout=20, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code!=200: return None
        orig=Image.open(BytesIO(r.content)).convert("RGB")
        W,H=1280,720
        canvas=Image.new("RGB",(W,H),(0,0,0))
        iw,ih=orig.size; ratio=min(W/iw,H/ih); nw,nh=int(iw*ratio),int(ih*ratio)
        resized=orig.resize((nw,nh), Image.LANCZOS)
        x=(W-nw)//2; y=(H-nh)//2; canvas.paste(resized,(x,y))
        draw=ImageDraw.Draw(canvas,"RGBA")
        try: b_small=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",20)
        except: b_small=ImageFont.load_default()
        bw,bh=300,36; bx=(W-bw)//2; by=H-bh-12
        draw.rounded_rectangle([bx, by, bx+bw, by+bh], radius=18, fill=(0,210,85,230))
        draw.text((bx+20, by+7), "🟢 UNFILTERED SCORES", font=b_small, fill=(255,255,255))
        bio=BytesIO(); canvas.save(bio, format="JPEG", quality=96); bio.seek(0); return bio
    except: return None

def post_fb(msg, img_bio):
    if len(FB_TOKEN)<50: return False
    try:
        url=f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
        files={"source":("hd.jpg", img_bio, "image/jpeg")}
        data={"message":msg, "access_token":FB_TOKEN}
        r=requests.post(url, files=files, data=data, timeout=35)
        print(f"FB {r.status_code}")
        return r.status_code==200
    except Exception as e:
        print(f"FB ERR {e}"); return False

def is_posted(k): return k in state.get("posted",[])
def mark(k):
    p=state.get("posted",[]); p.append(k); state["posted"]=p[-1000:]; save_state(state)

def process_live():
    print("Scanning live - CORRECT SCORE...")
    count=0
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for league_url in ESPN_LEAGUES:
        data=fetch_json(league_url)
        if not data: continue
        for ev in data.get("events",[]):
            try:
                if ev.get("date","")[:10]!=today_str: continue
                comp=ev.get("competitions",[{}])[0]
                status=comp.get("status",{}).get("type",{}).get("description","")
                state_type=comp.get("status",{}).get("type",{}).get("state","")
                name_state=comp.get("status",{}).get("type",{}).get("name","")
                competitors=comp.get("competitors",[])
                if len(competitors)<2: continue
                home=next((c for c in competitors if c.get("homeAway")=="home"), competitors[0])
                away=next((c for c in competitors if c.get("homeAway")=="away"), competitors[1])
                h_team=home.get("team",{}).get("displayName","Home")
                a_team=away.get("team",{}).get("displayName","Away")
                ev_id=ev.get("id","")
                h_score, a_score = get_correct_score(competitors)
                all_details = safe_list(comp.get("details",[]))
                running_h=0; running_a=0; goal_timeline=[]
                for d in all_details:
                    if not isinstance(d,dict): continue
                    t=d.get("type",{}).get("text","") if isinstance(d.get("type",{}),dict) else ""
                    if t in ["Goal","Own Goal","Penalty - Scored"]:
                        team_id=d.get("team",{}).get("id","") if isinstance(d.get("team",{}),dict) else ""
                        is_home=team_id==home.get("team",{}).get("id","")
                        if is_home: running_h+=1
                        else: running_a+=1
                        inv=safe_list(d.get("athletesInvolved",[]))
                        scorer=inv[0].get("displayName","") if inv and isinstance(inv[0],dict) else ""
                        assist=inv[1].get("displayName","") if len(inv)>1 and isinstance(inv[1],dict) else ""
                        minute=d.get("clock",{}).get("displayValue","") if isinstance(d.get("clock",{}),dict) else ""
                        goal_timeline.append({"id":d.get("id",""),"minute":minute.replace("'",""),"h":running_h,"a":running_a,"scorer":scorer,"assist":assist,"type":t})
                # 1. LINEUP EARLY - PRE MATCH
                if state_type=="pre" or "SCHEDULED" in name_state:
                    key=f"lineup_{ev_id}"
                    if not is_posted(key):
                        ld=fetch_real_lineups(ev_id)
                        if ld:
                            img=make_lineup_image(h_team, a_team, ld)
                            msg=f"📋 LINEUPS + BENCH\n{h_team} vs {a_team}\n\n{h_team}: {', '.join([n.split('(')[0][:20] for n in ld['home']['xi'][:11]])}\nBench: {', '.join(ld['home']['bench'][:4])}\n\n{a_team}: {', '.join([n.split('(')[0][:20] for n in ld['away']['xi'][:11]])}\nBench: {', '.join(ld['away']['bench'][:4])}\n\nWho wins? 👇 Follow 🟢 UNFILTERED SCORES"
                            if post_fb(msg, img): mark(key); count+=1
                # 2. KICKOFF SEPARATE
                if state_type=="in" or "Half" in status or "In Progress" in status:
                    key=f"kickoff_{ev_id}"
                    if not is_posted(key):
                        img=make_kickoff_image(h_team, a_team)
                        msg=f"🔥 KICK OFF!\n{h_team} vs {a_team}\nLIVE NOW!\n\nPredict score? 👇\nFollow 🟢 UNFILTERED SCORES"
                        if post_fb(msg, img): mark(key); count+=1
                    for g in goal_timeline:
                        key2=f"goal_{ev_id}_{g['id']}"
                        if is_posted(key2) or state_type=="post": continue
                        if "Own Goal" in g['type']:
                            msg=f"⚽ OWN GOAL! {g['minute']}'\n{h_team} {g['h']}-{g['a']} {a_team}\nBy {g['scorer']}\n\n🟢 UNFILTERED SCORES"
                            img=make_hd_image([f"OWN GOAL {g['minute']}'", f"{h_team} {g['h']}-{g['a']}", a_team, g['scorer']])
                        else:
                            gt="PENALTY!" if "Penalty" in g['type'] else "GOAL!"
                            msg=f"⚽ {gt} {g['minute']}'\n{h_team} {g['h']}-{g['a']} {a_team}\nScorer: {g['scorer']}\n\n🟢 UNFILTERED SCORES"
                            img=make_hd_image([f"{gt} {g['minute']}'", f"{h_team} {g['h']}-{g['a']}", a_team, g['scorer']])
                        if post_fb(msg, img): mark(key2); count+=1; time.sleep(1)
                    for d in all_details:
                        if not isinstance(d,dict): continue
                        t=d.get("type",{}).get("text","") if isinstance(d.get("type",{}),dict) else ""
                        if t in ["Red Card","Yellow-Red Card"]:
                            key2=f"red_{ev_id}_{d.get('id','')}"
                            if is_posted(key2) or state_type=="post": continue
                            inv=safe_list(d.get("athletesInvolved",[])); scorer=inv[0].get("displayName","") if inv and isinstance(inv[0],dict) else ""
                            minute=d.get("clock",{}).get("displayValue","") if isinstance(d.get("clock",{}),dict) else ""
                            msg=f"🟥 RED CARD! {minute}'\n{h_team} {h_score}-{a_score} {a_team}\n{scorer}\n\n🟢 UNFILTERED SCORES"
                            img=make_hd_image([f"RED CARD {minute}'", f"{h_team} {h_score}-{a_score}", a_team, scorer])
                            if post_fb(msg, img): mark(key2); count+=1
                if "Half" in status or "Final" in status or "FT" in status or "FINAL" in name_state or "HALFTIME" in name_state:
                    key=f"{status}_{ev_id}_{h_score}_{a_score}"
                    if not is_posted(key):
                        label="⏸️ HALFTIME" if "Half" in status or "HALFTIME" in name_state else "✅ FULL TIME"
                        msg=f"{label}\n{h_team} {h_score}-{a_score} {a_team}\n\nFollow 🟢 UNFILTERED SCORES"
                        img=make_hd_image([label.replace("⏸️ ","").replace("✅ ",""), f"{h_team} {h_score}-{a_score}", a_team])
                        if post_fb(msg, img): mark(key); count+=1
            except Exception as e:
                print(f"EV ERR {e}"); continue
    print(f"Live done {count}"); return count

def process_news():
    try:
        feeds=[("BBC","http://feeds.bbci.co.uk/sport/football/rss.xml"),("Sky","https://www.skysports.com/rss/12040")]
        for source_name, feed_url in feeds:
            feed=feedparser.parse(feed_url)
            for entry in feed.entries[:10]:
                title=entry.get("title","")
                if not title or not is_football_news(title): continue
                key=f"news_{title[:80]}"
                if is_posted(key): continue
                real_img=get_image_from_entry(entry)
                if not real_img: continue
                img_bio=make_real_image_news(real_img)
                if not img_bio: continue
                msg=f"🚨 {title}\n\nFollow 🟢 UNFILTERED SCORES ⚽\nSource: {source_name}"
                if post_fb(msg, img_bio): mark(key); return 1
    except Exception as e: print(f"NEWS ERR {e}")
    return 0

if __name__=="__main__":
    if len(FB_TOKEN)<50: print("ERROR TOKEN"); exit(0)
    start=time.time()
    print("V24 SHORT START")
    for i in range(25):
        try:
            process_live()
            if i%2==0: process_news()
        except Exception as e: print(f"MAIN ERR {e}")
        if time.time()-start>550: break
        time.sleep(20)
    print("DONE V24 SHORT")
