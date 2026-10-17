# V23 UNFILTERED SCORES - PERMANENT FIX - NO API KEY - FB PERMANENT TOKEN
import os, json, time, traceback, requests
from datetime import datetime
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import feedparser

FB_TOKEN = os.getenv("FB_TOKEN", "").strip()
FB_PAGE_ID = os.getenv("FB_PAGE_ID", "1293090263895541").strip()
print(f"=== V23 UNFILTERED PERMANENT FIX ===")
print(f"PAGE_ID={FB_PAGE_ID} TOKEN_LEN={len(FB_TOKEN)}")

STATE_FILE = "state.json"
def load_state():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except:
        return {"posted": [], "last_news": ""}

def save_state(s):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(s, f)
    except: pass

state = load_state()

# --- FIX FOR YOUR ERROR ---
def safe_list(x):
    if isinstance(x, list):
        return x
    if isinstance(x, dict):
        return [x]
    if not x:
        return []
    return [x]

def get_brand():
    return "🟢 UNFILTERED SCORES"

ESPN_LEAGUES = [
    "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard",
    "https://site.api.espn.com/apis/site/v2/sports/soccer/esp.1/scoreboard",
    "https://site.api.espn.com/apis/site/v2/sports/soccer/ita.1/scoreboard",
    "https://site.api.espn.com/apis/site/v2/sports/soccer/ger.1/scoreboard",
    "https://site.api.espn.com/apis/site/v2/sports/soccer/fra.1/scoreboard",
    "https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/scoreboard",
    "https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.europa/scoreboard"kpl livescores",
]

def fetch_json(url):
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code==200:
            return r.json()
    except Exception as e:
        print(f"FETCH ERR {e}")
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
        b_mid = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
        b_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26)
    except:
        b_big=b_mid=b_small=ImageFont.load_default()
    # GREEN WATERMARK TOP - YOUR BRAND
    draw.rectangle([0,0,W,88], fill=(0,200,83))
    draw.text((35,20), get_brand(), font=b_mid, fill=(255,255,255))
    y=130
    for i,line in enumerate(lines[:5]):
        f = b_big if i==0 else b_mid
        draw.text((50,y), line[:55], font=f, fill=(255,255,255))
        y+=92
    draw.text((50,H-45), datetime.now().strftime("%H:%M UTC • LIVE"), font=b_small, fill=(180,220,255))
    bio=BytesIO()
    img.save(bio, format="JPEG", quality=95)
    bio.seek(0)
    return bio

def post_fb(msg, img_bio):
    if len(FB_TOKEN)<50:
        print("NO TOKEN")
        return False
    try:
        url=f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
        files={"source":("hd.jpg", img_bio, "image/jpeg")}
        data={"message":msg, "access_token":FB_TOKEN}
        r=requests.post(url, files=files, data=data, timeout=30)
        print(f"FB POST {r.status_code} {r.text[:400]}")
        return r.status_code==200
    except Exception as e:
        print(f"FB ERR {e}")
        traceback.print_exc()
        return False

def is_posted(k): return k in state.get("posted",[])
def mark(k):
    p=state.get("posted",[])
    p.append(k)
    state["posted"]=p[-600:]
    save_state(state)

def process_live():
    print("Scanning live...")
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

                # LINEUPS - when match starts
                if state_type=="in" or status=="In Progress":
                    # lineup key once per match
                    key_line=f"lineup_{ev_id}"
                    if not is_posted(key_line):
                        # try get details for lineup
                        msg=f"🔥 LINEUP ALERT\n{h_team} vs {a_team}\nScore: {h_score}-{a_score}\nKICK-OFF LIVE!\n\n{get_brand()} - Fastest!"
                        img=make_hd_image([f"{h_team} vs {a_team}", f"{h_score}-{a_score}", "LIVE NOW", "LINEUPS OUT"])
                        if post_fb(msg, img):
                            mark(key_line)
                            count+=1

                # DETAILS - GOALS, RED, PENALTY - FIXED SAFE
                for d in safe_list(comp.get("details",[])):
                    if not isinstance(d, dict): continue
                    t = d.get("type",{})
                    t_text = t.get("text","") if isinstance(t, dict) else str(t)
                    minute = d.get("clock",{}).get("displayValue","") if isinstance(d.get("clock",{}), dict) else ""
                    # athletes
                    scorer=""; assist=""
                    inv = safe_list(d.get("athletesInvolved",[]))
                    if inv:
                        scorer = inv[0].get("displayName","") if isinstance(inv[0], dict) else ""
                        if len(inv)>1:
                            assist = inv[1].get("displayName","")

                    # GOAL
                    if t_text in ["Goal","Own Goal","Penalty - Scored"]:
                        key=f"goal_{ev_id}_{d.get('id','')}_{minute}"
                        if is_posted(key): continue
                        goal_type = "PENALTY GOAL" if "Penalty" in t_text else ("OWN GOAL" if "Own" in t_text else "GOAL")
                        assist_txt = f"\nAssist: {assist}" if assist else ""
                        msg=f"⚽ {goal_type}! {minute}'\n{h_team} {h_score}-{a_score} {a_team}\nScorer: {scorer}{assist_txt}\n\n{get_brand()}"
                        img=make_hd_image([f"{goal_type}! {minute}'", f"{h_team} {h_score}-{a_score}", a_team, scorer])
                        if post_fb(msg, img):
                            mark(key)
                            count+=1
                            time.sleep(2)

                    # RED CARD
                    if t_text in ["Red Card","Yellow-Red Card"]:
                        key=f"red_{ev_id}_{d.get('id','')}"
                        if is_posted(key): continue
                        msg=f"🟥 RED CARD! {minute}'\n{h_team} {h_score}-{a_score} {a_team}\nPlayer: {scorer}\n\n{get_brand()}"
                        img=make_hd_image([f"RED CARD {minute}'", f"{h_team} {h_score}-{a_score}", a_team, scorer])
                        if post_fb(msg, img):
                            mark(key)
                            count+=1

                # HT / FT
                if status in ["Halftime","Full Time","Final","FT"]:
                    key=f"{status}_{ev_id}_{h_score}_{a_score}"
                    if is_posted(key): continue
                    label="⏸️ HALFTIME" if "Half" in status else "✅ FULL TIME"
                    msg=f"{label}\n{h_team} {h_score}-{a_score} {a_team}\n\n{get_brand()} - Final Result"
                    img=make_hd_image([label.replace("⏸️ ","").replace("✅ ",""), f"{h_team} {h_score}-{a_score}", a_team])
                    if post_fb(msg, img):
                        mark(key)
                        count+=1

            except Exception as e:
                print(f"EV ERR {e}")
                continue
        time.sleep(1)
    print(f"Live done {count}")
    return count

def process_news():
    # Breaking news - ESPN RSS free, no API key
    try:
        feeds=["http://www.espn.com/espn/rss/soccer/news","https://www.skysports.com/rss/12040"]
        for feed_url in feeds[:1]:
            feed=feedparser.parse(feed_url)
            for entry in feed.entries[:3]:
                title=entry.get("title","")
                if not title: continue
                key=f"news_{title[:60]}"
                if is_posted(key): continue
                if any(w in title.lower() for w in ["transfer","injury","breaking","official","signs","deal"]):
                    msg=f"🚨 BREAKING NEWS\n{title}\n\n{get_brand()} - Fastest Football News!"
                    img=make_hd_image([ "BREAKING NEWS", title[:45], title[45:90] ])
                    if post_fb(msg, img):
                        mark(key)
                        return 1
    except Exception as e:
        print(f"NEWS ERR {e}")
    return 0

if __name__=="__main__":
    if len(FB_TOKEN)<50:
        print("ERROR: Set FB_TOKEN + FB_PAGE_ID in Secrets")
        exit(0)
    start=time.time()
    for i in range(120): # 60 mins
        try:
            process_live()
            if i%4==0:
                process_news()
        except Exception as e:
            print(f"MAIN ERR {e}")
            traceback.print_exc()
        if time.time()-start>3300:
            break
        time.sleep(30)
    print("DONE V23")
