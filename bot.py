# bot.py V32 - REAL NEWS + REAL PERSON FACE + 4 PER HOUR + GOALS + BRAND 🟢
import os, json, requests, re, textwrap, xml.etree.ElementTree as ET, random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

PAGE_ID=os.getenv("PAGE_ID")
PAGE_TOKEN=os.getenv("PAGE_ACCESS_TOKEN")
STATE_FILE="posted_state.json"
EAT=ZoneInfo("Africa/Nairobi")

NAMES={"eng.1":"Premier League","esp.1":"La Liga","uefa.champions":"UCL","ken.1":"KPL"}
PRIORITY=["eng.1","esp.1","uefa.champions","ken.1"]
BIG_BG={"real madrid":(255,255,255),"barcelona":(20,20,120),"manchester city":(108,171,223),"arsenal":(239,1,7),"liverpool":(200,16,46),"chelsea":(3,70,148),"man utd":(218,0,0),"bayern":(220,5,45),"psg":(0,38,84)}

# --- STATE FIXED - NEVER KeyError ---
def load_state():
    default={"lineup":{},"goals":{},"ht":{},"ft":{},"last":{},"news":[],"last_news_time":0}
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
        for u in [f"https://a.espncdn.com/i/headshots/soccer/players/full/{espn_id}.png", f"https://a.espncdn.com/combiner/i?img=%2Fi%2Fheadshots%2Fsoccer%2Fplayers%2Ffull%2F{espn_id}.png&w=500&h=500"]:
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
        for p in (j.get("player",[]) or [])[:2]:
            cut=p.get("strCutout") or p.get("strThumb")
            if cut:
                im=dl(cut)
                if im: return im
    except: pass
    return None

# --- NEWS SOURCES - ALL WITH REAL IMAGES ---
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

# Extract person who spoke
KNOWN_NAMES=["Saka","Arteta","Haaland","Guardiola","Mbappe","Vinicius","Bellingham","Salah","Klopp","Ancelotti","Messi","Ronaldo","Rashford","Odegaard","Palmer","Foden","Kane","Lewandowski","Yamal","Pedri"]
def extract_speaker(title):
    t=title.lower()
    for n in KNOWN_NAMES:
        if n.lower() in t: return n
    m=re.match(r"^([A-Z][a-z]+)", title)
    if m: return m.group(1)
    return None

def make_news_img(real_img, speaker_face, title):
    W,H=1080,1350
    bg=Image.new("RGB",(W,H),(12,12,12))
    # Article real image top 70%
    try:
        art=real_img.resize((W, 900))
        bg.paste(art,(0,0))
    except: pass
    # Speaker face circle bottom right if found
    if speaker_face:
        try:
            sf=speaker_face.resize((280,280))
            # circle mask
            mask=Image.new("L",(280,280),0)
            md=ImageDraw.Draw(mask); md.ellipse([0,0,280,280], fill=255)
            bg.paste(sf,(750,700),mask)
            d0=ImageDraw.Draw(bg); d0.ellipse([750,700,1030,980], outline=(0,255,100), width=8)
        except: pass

    d=ImageDraw.Draw(bg)
    try:
        fb=ImageFont.truetype("DejaVuSans-Bold.ttf",40)
        fs=ImageFont.truetype("DejaVuSans-Bold.ttf",32)
    except: fb=fs=ImageFont.load_default()

    # Title box with brand 🟢
    d.rounded_rectangle([0,900,W,1350], radius=0, fill=(0,0,0))
    d.rounded_rectangle([20,20,W-20,80], radius=15, fill=(0,255,100))
    d.text((40,30), "Unfiltered Scores 🟢 • BREAKING", font=fs, fill=(0,0,0))

    wrapped=textwrap.wrap(title, 36)[:4]
    y=930
    for line in wrapped:
        d.text((30,y), line, font=fb, fill=(255,255,255)); y+=48

    d.rounded_rectangle([20,1260,W-20,1330], radius=15, fill=(0,255,100))
    d.text((40,1270), "Unfiltered Scores 🟢", font=fs, fill=(0,0,0))

    path="/tmp/news.png"
    bg.save(path)
    return path

def post(msg, path):
    try:
        url=f"https://graph.facebook.com/v20.0/{PAGE_ID}/photos"
        with open(path,"rb") as f:
            r=requests.post(url, data={"caption":msg,"access_token":PAGE_TOKEN}, files={"source":f}, timeout=20)
        print(f"POST {r.status_code}")
        return r.status_code==200
    except Exception as e: print(e); return False

# --- SCORES PART (same as V30) ---
def get_bg(name):
    nl=name.lower()
    for k,v in BIG_BG.items():
        if k in nl: return v
    return (10,22,10)

def make_goal_img(h,a,hs,as_,lg,minute,scorer,h_id,a_id,player_name,espn_id):
    bg=get_bg(h); W,H=1080,1350
    img=Image.new("RGB",(W,H),bg); d=ImageDraw.Draw(img)
    try: fb=ImageFont.truetype("DejaVuSans-Bold.ttf",95); fm=ImageFont.truetype("DejaVuSans-Bold.ttf",48); fs=ImageFont.truetype("DejaVuSans-Bold.ttf",36); fsmall=ImageFont.truetype("DejaVuSans.ttf",30)
    except: fb=fm=fs=fsmall=ImageFont.load_default()
    d.rounded_rectangle([30,20,W-30,85], radius=20, fill=(0,255,100))
    d.text((50,30), f"Unfiltered Scores 🟢 • {lg}", font=fs, fill=(0,0,0))
    d.text((750,30), minute, font=fs, fill=(0,0,0))
    rp=get_real_scorer_photo(player_name, espn_id)
    if rp:
        rp=rp.resize((520,520)); d.ellipse([270,110,810,650], fill=(255,255,255)); img.paste(rp,(280,120),rp)
    def badge(tid,x):
        if not tid: return
        b=dl(f"https://a.espncdn.com/i/teamlogos/soccer/500/{tid}.png")
        if b: b=b.resize((180,180)); img.paste(b,(x,160),b)
    badge(h_id,80); badge(a_id,820)
    d.text((60,400), h[:14].upper(), font=fm, fill=(255,255,255)); d.text((800,400), a[:14].upper(), font=fm, fill=(255,255,255))
    d.rounded_rectangle([280,700,800,820], radius=30, fill=(255,255,255)); d.text((340,720), f"{hs} - {as_}", font=fb, fill=(0,0,0))
    if scorer:
        for i,ln in enumerate(textwrap.wrap(scorer,40)[:3]): d.text((60,870+i*48), ln, font=fsmall, fill=(255,255,255))
    d.rounded_rectangle([30,1240,W-30,1320], radius=20, fill=(0,255,100)); d.text((50,1255), f"Unfiltered Scores 🟢 LIVE • {player_name}", font=fs, fill=(0,0,0))
    path="/tmp/m.png"; img.save(path); return path

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
        return {"d":det}
    except: return {"d":[]}

def main():
    st=load_state()
    now=datetime.now(EAT)
    # ---- LIVE SCORES ----
    all_ev=[]
    with ThreadPoolExecutor(max_workers=4) as ex:
        for lst in ex.map(get_sb, PRIORITY): all_ev.extend(lst)
    live=[e for e in all_ev if e["competitions"][0]["status"]["type"]["name"] in ["STATUS_IN_PROGRESS","STATUS_HALFTIME"]]
    if not live: live=all_ev[:12]
    print(f"V32 LIVE:{len(live)}")

    sums={}
    with ThreadPoolExecutor(max_workers=10) as ex:
        ids=[(e["id"], e["_code"]) for e in live]
        for e,s in zip(live, ex.map(get_sum, ids)): sums[e["id"]]=s

    posted=0
    for ev in live:
        ev_id=ev["id"]; comp=ev["competitions"][0]; status=comp["status"]["type"]["name"]; short=comp["status"]["type"].get("shortDetail","")
        comps=comp["competitors"]
        try: h=next(x for x in comps if x["homeAway"]=="home"); a=next(x for x in comps if x["homeAway"]=="away")
        except: continue
        hn,an=h["team"]["displayName"],a["team"]["displayName"]; hid,aid=h["team"].get("id"),a["team"].get("id"); hs,as_=str(h.get("score","0")),str(a.get("score","0")); lg=ev["_lname"]
        summ=sums.get(ev_id,{"d":[]}); details=summ["d"]; m=re.search(r"(\d+)'", short); minute=int(m.group(1)) if m else 0
        last=st.get("last",{}).get(ev_id,"0-0")
        if status in ["STATUS_IN_PROGRESS","STATUS_HALFTIME"] and last!=f"{hs}-{as_}":
            if not (last=="0-0" and hs=="0" and as_=="0"):
                gid=f"{ev_id}_{hs}-{as_}"
                if gid not in st.get("goals",{}):
                    scorer_txt, pid, pname = f"GOAL! {hs}-{as_}", None, "Unknown"
                    for d in details[-5:]:
                        if "goal" in str(d.get("type","")).lower():
                            scorer_txt=d.get("text",""); pid=d.get("athlete",{}).get("id"); pname=d.get("athlete",{}).get("displayName","") or scorer_txt.split(" - ")[0][:20]; break
                    if not pname or pname=="Unknown":
                        if " - " in scorer_txt: pname=scorer_txt.split(" - ")[0].split("(")[0].strip()
                    img=make_goal_img(hn,an,hs,as_,lg,f"{minute}' GOAL",scorer_txt,hid,aid,pname,pid)
                    if post(f"⚽ GOAL! {minute}' 🟢 {pname}\n\n{lg}\n{hn} {hs} - {as_} {an}\n\n{scorer_txt}\n\nUnfiltered Scores 🟢 LIVE\n#UnfilteredScores 🟢", img):
                        st.setdefault("goals",{})[gid]=1; posted+=1
        st.setdefault("last",{})[ev_id]=f"{hs}-{as_}"

    # ---- FOOTBALL NEWS 3-4 PER HOUR WITH REAL IMAGE + SPEAKER FACE ----
    last_t=st.get("last_news_time",0)
    if (datetime.now().timestamp() - last_t) > 900: # 15 min = 4 per hour
        all_news=fetch_espn_news() + fetch_rss_news()
        random.shuffle(all_news)
        for n in all_news[:8]:
            nid=n["title"][:50]
            if nid in st.get("news",[]): continue
            speaker=extract_speaker(n["title"])
            print(f"NEWS TRY {n['title']} speaker={speaker}")
            real_img=dl(n["img"])
            if not real_img: continue
            speaker_face=get_real_scorer_photo(speaker) if speaker else None
            img_path=make_news_img(real_img, speaker_face, n["title"])
            caption=f"{n['title']}\n\n{n['desc']}\n\n🗣️ {speaker} speaks\n\nSource: {n['link']}\n\nUnfiltered Scores 🟢\n#UnfilteredScores 🟢 #FootballNews"
            if post(caption, img_path):
                st.setdefault("news",[]).append(nid)
                if len(st["news"])>100: st["news"]=st["news"][-100:]
                st["last_news_time"]=datetime.now().timestamp()
                posted+=1
                break # post only 1 news per run

    print(f"V32 DONE {posted}")
    save_state(st)

if __name__=="__main__": main()
