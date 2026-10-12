# bot.py V34 FULL - LIVE + LINEUP + RED + HT + FT + GOAL 10sec + NEWS + REAL STADIUM PHOTO + BRAND 🟢
import os, json, requests, re, textwrap, xml.etree.ElementTree as ET, random, time
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

PAGE_ID=os.getenv("PAGE_ID")
PAGE_TOKEN=os.getenv("PAGE_ACCESS_TOKEN")
STATE_FILE="posted_state.json"
EAT=ZoneInfo("Africa/Nairobi")

NAMES={"eng.1":"Premier League","esp.1":"La Liga","uefa.champions":"UCL","ken.1":"KPL","ita.1":"Serie A","ger.1":"Bundesliga"}
PRIORITY=["eng.1","esp.1","uefa.champions","ita.1","ger.1","ken.1"]
BIG_BG={"real madrid":(255,255,255),"barcelona":(20,20,120),"man city":(108,171,223),"arsenal":(239,1,7),"liverpool":(200,16,46),"chelsea":(3,70,148),"man utd":(218,0,0),"bayern":(220,5,45),"psg":(0,38,84)}

def load_state():
    default={"lineup":{},"goals":{},"ht":{},"ft":{},"last":{},"red":{},"news":[],"last_news_time":0,"live_posted":{}}
    try:
        with open(STATE_FILE) as f:
            s=json.load(f)
            for k,v in default.items(): s.setdefault(k,v)
            return s
    except: return default
def save_state(s):
    with open(STATE_FILE,"w") as f: json.dump(s,f)

def dl(url):
    try:
        r=requests.get(url, timeout=6, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code==200 and len(r.content)>3000:
            return Image.open(BytesIO(r.content)).convert("RGBA")
    except: return None

def get_real_scorer_photo(player_name, espn_id=None):
    if not player_name: return None
    if espn_id:
        for u in [f"https://a.espncdn.com/i/headshots/soccer/players/full/{espn_id}.png"]:
            im=dl(u)
            if im: return im
    try:
        s=requests.get(f"https://api.sofascore.app/api/v1/search/all?q={player_name}", timeout=5, headers={"User-Agent":"Mozilla/5.0"}).json()
        for res in s.get("results",[]):
            if res.get("type")=="player":
                pid=res.get("entity",{}).get("id")
                if pid:
                    im=dl(f"https://api.sofascore.app/api/v1/player/{pid}/image")
                    if im: return im
    except: pass
    try:
        j=requests.get(f"https://www.thesportsdb.com/api/v1/json/3/searchplayers.php?p={player_name}", timeout=5).json()
        for p in (j.get("player",[]) or [])[:1]:
            cut=p.get("strCutout") or p.get("strThumb")
            if cut:
                im=dl(cut)
                if im: return im
    except: pass
    return None

# === REAL PHOTO FROM STADIUM / GROUND - ALL SOURCES ===
def get_real_match_photo(ev_id, league_code, home, away):
    # 1. SofaScore event image (real stadium action)
    try:
        # search sofascore event by teams
        s=requests.get(f"https://api.sofascore.app/api/v1/search/all?q={home} {away}", timeout=4, headers={"User-Agent":"Mozilla/5.0"}).json()
        for res in s.get("results",[])[:3]:
            if res.get("type")=="event":
                eid=res.get("entity",{}).get("id")
                if eid:
                    im=dl(f"https://api.sofascore.app/api/v1/event/{eid}/image")
                    if im: return im
    except: pass
    # 2. TheSportsDB real thumb from ground
    try:
        q=f"{home}_vs_{away}"
        j=requests.get(f"https://www.thesportsdb.com/api/v1/json/3/searchevents.php?e={q}", timeout=4).json()
        ev=j.get("event",[]) or []
        if ev and ev[0].get("strThumb"):
            im=dl(ev[0]["strThumb"])
            if im: return im
    except: pass
    # 3. ESPN Getty image from summary
    try:
        j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/summary?event={ev_id}", timeout=4).json()
        pics=j.get("header",{}).get("pics") or j.get("pics") or []
        if pics:
            im=dl(pics[0].get("href") or pics[0].get("url"))
            if im: return im
    except: pass
    return None

RSS_FEEDS=[
    "https://feeds.bbci.co.uk/sport/football/rss.xml",
    "https://www.skysports.com/rss/0,20514,11095,00.xml",
    "https://www.goal.com/feeds/en/news",
    "https://e00-marca.uecdn.es/rss/futbol/en.xml",
]
def fetch_rss_news():
    news=[]
    for rss in RSS_FEEDS:
        try:
            r=requests.get(rss, timeout=6, headers={"User-Agent":"Mozilla/5.0"})
            root=ET.fromstring(r.content)
            for item in root.findall(".//item")[:6]:
                title=item.findtext("title","") or ""
                link=item.findtext("link","") or ""
                desc=item.findtext("description","") or ""
                img=None
                enc=item.find("enclosure")
                if enc is not None: img=enc.get("url")
                if not img:
                    ns=item.find("{http://search.yahoo.com/mrss/}content")
                    if ns is not None: img=ns.get("url")
                if not img:
                    m=re.search(r'<img[^>]+src="([^"]+)"', desc)
                    if m: img=m.group(1)
                if title and img:
                    news.append({"title":title.strip(),"link":link,"img":img,"desc":re.sub('<[^<]+?>','',desc)[:200]})
        except: continue
    return news
def fetch_espn_news():
    news=[]
    try:
        j=requests.get("https://site.api.espn.com/apis/site/v2/sports/soccer/news", timeout=6).json()
        for a in j.get("articles",[])[:10]:
            title=a.get("headline","")
            link=a.get("links",{}).get("web",{}).get("href","")
            imgs=a.get("images",[])
            img=imgs[0].get("url") if imgs else None
            if title and img:
                news.append({"title":title,"link":link,"img":img,"desc":a.get("description","")[:200]})
    except: pass
    return news

def extract_speaker(title):
    for n in ["Saka","Arteta","Haaland","Guardiola","Mbappe","Vinicius","Bellingham","Salah","Klopp","Ancelotti","Messi","Ronaldo","Rashford","Odegaard","Palmer","Foden","Kane","Lewandowski","Yamal"]:
        if n.lower() in title.lower(): return n
    return None

def make_news_img(real_img):
    W,H=1080,1350
    try:
        rw, rh = real_img.size
        real_img = real_img.crop((0, 0, rw, int(rh * 0.82)))
        bg = real_img.resize((W, H))
    except: bg = real_img.resize((W, H))
    d=ImageDraw.Draw(bg)
    try: fs=ImageFont.truetype("DejaVuSans-Bold.ttf",34)
    except: fs=ImageFont.load_default()
    d.rounded_rectangle([15,15,W-15,75], radius=18, fill=(0,255,100))
    d.text((35,25), "Unfiltered Scores 🟢 • BREAKING", font=fs, fill=(0,0,0))
    path="/tmp/news.png"; bg.save(path, quality=95); return path

def post(msg, path):
    try:
        url=f"https://graph.facebook.com/v20.0/{PAGE_ID}/photos"
        with open(path,"rb") as f:
            r=requests.post(url, data={"caption":msg,"access_token":PAGE_TOKEN}, files={"source":f}, timeout=20)
        print(f"POST {r.status_code}")
        return r.status_code==200
    except Exception as e: print(e); return False

def get_bg(name):
    nl=name.lower()
    for k,v in BIG_BG.items():
        if k in nl: return v
    return (10,22,10)

def make_img_with_stadium(home, away, home_id, away_id, score_txt, lg, top_txt, bottom_txt, real_stadium, scorer_face=None):
    W,H=1080,1350
    # Real stadium as background
    if real_stadium:
        try:
            bg=real_stadium.resize((W,H))
            # Darken for text visibility
            overlay=Image.new("RGBA",(W,H),(0,0,0,110))
            bg=Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
        except: bg=Image.new("RGB",(W,H),get_bg(home))
    else:
        bg=Image.new("RGB",(W,H),get_bg(home))
    d=ImageDraw.Draw(bg)
    try: fb=ImageFont.truetype("DejaVuSans-Bold.ttf",95); fm=ImageFont.truetype("DejaVuSans-Bold.ttf",48); fs=ImageFont.truetype("DejaVuSans-Bold.ttf",36); fsmall=ImageFont.truetype("DejaVuSans.ttf",30)
    except: fb=fm=fs=fsmall=ImageFont.load_default()
    d.rounded_rectangle([30,20,W-30,85], radius=20, fill=(0,255,100))
    d.text((50,30), f"Unfiltered Scores 🟢 • {lg}", font=fs, fill=(0,0,0))
    d.text((750,30), top_txt[:18], font=fs, fill=(255,255,255))
    # scorer face circle if available
    if scorer_face:
        try:
            sf=scorer_face.resize((420,420))
            mask=Image.new("L",(420,420),0); ImageDraw.Draw(mask).ellipse([0,0,420,420], fill=255)
            bg.paste(sf,(330,140),mask)
            d.ellipse([330,140,750,560], outline=(0,255,100), width=6)
        except: pass
    else:
        # team badges
        def badge(tid,x):
            if not tid: return
            b=dl(f"https://a.espncdn.com/i/teamlogos/soccer/500/{tid}.png")
            if b: b=b.resize((180,180)); bg.paste(b,(x,200),b)
        badge(home_id,80); badge(away_id,820)
    d.text((60,450), home[:14].upper(), font=fm, fill=(255,255,255)); d.text((800,450), away[:14].upper(), font=fm, fill=(255,255,255))
    d.rounded_rectangle([280,700,800,820], radius=30, fill=(255,255,255)); d.text((340,720), score_txt, font=fb, fill=(0,0,0))
    d.rounded_rectangle([30,1240,W-30,1320], radius=20, fill=(0,255,100)); d.text((50,1255), bottom_txt[:52], font=fs, fill=(0,0,0))
    path="/tmp/m.png"; bg.save(path); return path

def get_sb(lg):
    try:
        j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/scoreboard", timeout=4).json()
        evs=[]
        for ev in j.get("events",[]):
            ev["_code"]=lg; ev["_lname"]=NAMES.get(lg,lg); evs.append(ev)
        return evs
    except: return []
def get_sum(args):
    ev_id, code=args
    try:
        j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/summary?event={ev_id}", timeout=4).json()
        det=j.get("header",{}).get("competitions",[{}])[0].get("details",[]) or []
        line=j.get("lineups") or j.get("rosters") or []
        return {"d":det,"l":line,"raw":j}
    except: return {"d":[],"l":[],"raw":{}}
def get_lineup_text(lineups):
    txt=""
    try:
        for team in lineups[:2]:
            txt+=f"{team.get('team',{}).get('displayName','')}: "
            players=[p.get('athlete',{}).get('displayName','') for p in team.get('roster',[])[:11]]
            txt+=", ".join(players[:11])+"\n"
    except: pass
    return txt[:400]

def run_once(st):
    all_ev=[]
    with ThreadPoolExecutor(max_workers=6) as ex:
        for lst in ex.map(get_sb, PRIORITY): all_ev.extend(lst)
    live=[e for e in all_ev if e["competitions"][0]["status"]["type"]["name"] in ["STATUS_IN_PROGRESS","STATUS_HALFTIME","STATUS_SCHEDULED"]]
    print(f"LIVE+SCHED {len(live)}")
    sums={}
    with ThreadPoolExecutor(max_workers=12) as ex:
        ids=[(e["id"], e["_code"]) for e in live]
        for e,s in zip(live, ex.map(get_sum, ids)): sums[e["id"]]=s

    posted=0
    for ev in live:
        ev_id=ev["id"]; code=ev["_code"]; comp=ev["competitions"][0]; status=comp["status"]["type"]["name"]; short=comp["status"]["type"].get("shortDetail",""); state=comp["status"]["type"].get("state","")
        comps=comp["competitors"]
        try: h=next(x for x in comps if x["homeAway"]=="home"); a=next(x for x in comps if x["homeAway"]=="away")
        except: continue
        hn,an=h["team"]["displayName"],a["team"]["displayName"]; hid,aid=h["team"].get("id"),a["team"].get("id"); hs,as_=str(h.get("score","0")),str(a.get("score","0")); lg=ev["_lname"]
        summ=sums.get(ev_id,{"d":[],"l":[],"raw":{}}); details=summ["d"]; lineups=summ["l"]
        m=re.search(r"(\d+)'", short); minute=int(m.group(1)) if m else 0
        real_ground=get_real_match_photo(ev_id, code, hn, an)

        # 1. LINEUP - 60 mins before
        if status=="STATUS_SCHEDULED" and ev_id not in st.get("lineup",{}):
            if lineups and len(lineups)>=1:
                txt=get_lineup_text(lineups)
                if txt:
                    img=make_img_with_stadium(hn,an,hid,aid,"VS",lg,"LINEUP",f"Unfiltered Scores 🟢 {hn} vs {an}",real_ground)
                    if post(f"📋 LINEUP 🟢 {lg}\n\n{hn} vs {an}\n\n{txt}\n\nKickoff {short}\n\nUnfiltered Scores 🟢\n#UnfilteredScores 🟢", img):
                        st.setdefault("lineup",{})[ev_id]=1; posted+=1

        # 2. LIVE START
        if status in ["STATUS_IN_PROGRESS"] and minute<=3 and ev_id not in st.get("live_posted",{}):
            img=make_img_with_stadium(hn,an,hid,aid,f"{hs}-{as_}",lg,"LIVE",f"Unfiltered Scores 🟢 LIVE NOW",real_ground)
            if post(f"🔴 LIVE NOW 🟢\n\n{lg}\n{hn} {hs} - {as_} {an}\n\n{short}\n\nUnfiltered Scores 🟢\n#UnfilteredScores 🟢", img):
                st.setdefault("live_posted",{})[ev_id]=1; posted+=1

        # 3. GOAL + RED CARD
        last=st.get("last",{}).get(ev_id,"0-0")
        if status in ["STATUS_IN_PROGRESS","STATUS_HALFTIME"] and last!=f"{hs}-{as_}":
            if not (last=="0-0" and hs=="0" and as_=="0"):
                gid=f"{ev_id}_{hs}-{as_}"
                if gid not in st.get("goals",{}):
                    scorer_txt, pid, pname, is_red=False, None, "Unknown", False
                    for d in details[-8:]:
                        t=str(d.get("type","")).lower()
                        if "goal" in t:
                            scorer_txt=d.get("text",""); pid=d.get("athlete",{}).get("id"); pname=d.get("athlete",{}).get("displayName","") or scorer_txt.split(" - ")[0][:20]; break
                        if "red" in t or "redcard" in t:
                            scorer_txt=d.get("text",""); pid=d.get("athlete",{}).get("id"); pname=d.get("athlete",{}).get("displayName",""); is_red=True; break
                    if not pname or pname=="Unknown":
                        if " - " in scorer_txt: pname=scorer_txt.split(" - ")[0].split("(")[0].strip()
                    face=get_real_scorer_photo(pname, pid)
                    if is_red:
                        if ev_id+f"red{minute}{pname}" not in st.get("red",{}):
                            img=make_img_with_stadium(hn,an,hid,aid,f"{hs}-{as_}",lg,f"{minute}' RED",f"Unfiltered Scores 🟢 RED CARD {pname}",real_ground,face)
                            if post(f"🟥 RED CARD! {minute}' 🟢 {pname}\n\n{lg}\n{hn} {hs} - {as_} {an}\n\n{scorer_txt}\n\nUnfiltered Scores 🟢\n#UnfilteredScores 🟢", img):
                                st.setdefault("red",{})[ev_id+f"red{minute}{pname}"]=1; posted+=1
                    else:
                        img=make_img_with_stadium(hn,an,hid,aid,f"{hs}-{as_}",lg,f"{minute}' GOAL",f"Unfiltered Scores 🟢 GOAL {pname}",real_ground,face)
                        if post(f"⚽ GOAL! {minute}' 🟢 {pname}\n\n{lg}\n{hn} {hs} - {as_} {an}\n\n{scorer_txt}\n\nUnfiltered Scores 🟢 LIVE\n#UnfilteredScores 🟢", img):
                            st.setdefault("goals",{})[gid]=1; posted+=1
        st.setdefault("last",{})[ev_id]=f"{hs}-{as_}"

        # 4. HALFTIME
        if status=="STATUS_HALFTIME" and ev_id not in st.get("ht",{}):
            img=make_img_with_stadium(hn,an,hid,aid,f"{hs}-{as_}",lg,"HT",f"Unfiltered Scores 🟢 HALFTIME",real_ground)
            if post(f"⏸️ HALFTIME 🟢\n\n{lg}\n{hn} {hs} - {as_} {an}\n\nUnfiltered Scores 🟢\n#UnfilteredScores 🟢", img):
                st.setdefault("ht",{})[ev_id]=1; posted+=1

        # 5. FULL TIME
        if status in ["STATUS_FINAL","STATUS_FULL_TIME"] and ev_id not in st.get("ft",{}):
            img=make_img_with_stadium(hn,an,hid,aid,f"{hs}-{as_}",lg,"FT",f"Unfiltered Scores 🟢 FULL TIME",real_ground)
            if post(f"✅ FULL TIME 🟢\n\n{lg}\n{hn} {hs} - {as_} {an}\n\nUnfiltered Scores 🟢\n#UnfilteredScores 🟢", img):
                st.setdefault("ft",{})[ev_id]=1; posted+=1

    return posted

def main():
    st=load_state()
    total=0
    # 10 SECOND LOOP - 6 times
    for i in range(6):
        print(f"10sec loop {i+1}/6")
        total+=run_once(st)
        save_state(st)
        if i<5: time.sleep(10)

    # NEWS - 4 per hour - REAL IMAGE CLEAN TOP ONLY
    if (datetime.now().timestamp() - st.get("last_news_time",0)) > 900:
        all_news=fetch_espn_news() + fetch_rss_news()
        random.shuffle(all_news)
        for n in all_news[:10]:
            nid=n["title"][:60]
            if nid in st.get("news",[]): continue
            real=dl(n["img"])
            if not real: continue
            img=make_news_img(real)
            cap=f"{n['title']}\n\n{n['desc']}\n\nSource: {n['link']}\n\nUnfiltered Scores 🟢\n#UnfilteredScores 🟢 #FootballNews"
            if post(cap, img):
                st.setdefault("news",[]).append(nid)
                if len(st["news"])>150: st["news"]=st["news"][-150:]
                st["last_news_time"]=datetime.now().timestamp()
                total+=1
                break
    print(f"V34 DONE {total}")
    save_state(st)

if __name__=="__main__": main()
