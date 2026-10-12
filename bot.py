# bot.py V30 - FIXED KeyError last + REAL SCORER PHOTO + BRAND 🟢
import os, json, requests, re, textwrap
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

PAGE_ID=os.getenv("PAGE_ID")
PAGE_TOKEN=os.getenv("PAGE_ACCESS_TOKEN")
STATE_FILE="posted_state.json"
EAT=ZoneInfo("Africa/Nairobi")

NAMES={"eng.1":"Premier League","esp.1":"La Liga","uefa.champions":"UCL","ken.1":"KPL","ger.1":"Bundesliga","ita.1":"Serie A","fra.1":"Ligue 1"}
PRIORITY=["eng.1","esp.1","uefa.champions","ken.1"]

BIG_BG={
    "real madrid":(255,255,255), "barcelona":(20,20,120), "manchester city":(108,171,223),
    "arsenal":(239,1,7), "liverpool":(200,16,46), "chelsea":(3,70,148),
    "manchester united":(218,0,0), "bayern":(220,5,45), "psg":(0,38,84), "atletico":(220,0,0)
}

# === FIXED LOAD_STATE - AUTO FIXES OLD FILE - NO MORE KeyError ===
def load_state():
    default = {"lineup":{},"goals":{},"ht":{},"ft":{},"last":{},"news":[]}
    try:
        with open(STATE_FILE) as f:
            s=json.load(f)
            # Auto-upgrade old file that misses keys like 'last'
            for k,v in default.items():
                s.setdefault(k, v)
            return s
    except:
        return default

def save_state(s):
    with open(STATE_FILE,"w") as f: json.dump(s,f)

def dl(url):
    try:
        r=requests.get(url, timeout=4, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code==200 and len(r.content)>2000:
            return Image.open(BytesIO(r.content)).convert("RGBA")
    except: return None

def get_real_scorer_photo(player_name, espn_id=None):
    if espn_id:
        for url in [
            f"https://a.espncdn.com/i/headshots/soccer/players/full/{espn_id}.png",
            f"https://a.espncdn.com/combiner/i?img=%2Fi%2Fheadshots%2Fsoccer%2Fplayers%2Ffull%2F{espn_id}.png&w=400&h=400"
        ]:
            img=dl(url)
            if img: return img
    try:
        s=requests.get(f"https://api.sofascore.app/api/v1/search/all?q={player_name}", timeout=4, headers={"User-Agent":"Mozilla/5.0"}).json()
        for res in s.get("results",[]):
            if res.get("type")=="player":
                pid=res.get("entity",{}).get("id")
                if pid:
                    img=dl(f"https://api.sofascore.app/api/v1/player/{pid}/image")
                    if img: return img
    except: pass
    try:
        j=requests.get(f"https://www.thesportsdb.com/api/v1/json/3/searchplayers.php?p={player_name}", timeout=4).json()
        for p in (j.get("player",[]) or [])[:2]:
            cut=p.get("strCutout") or p.get("strThumb")
            if cut:
                img=dl(cut)
                if img: return img
    except: pass
    try:
        j=requests.get(f"https://en.wikipedia.org/w/api.php?action=query&titles={player_name}&prop=pageimages&format=json&pithumbsize=400", timeout=4).json()
        for pg in j.get("query",{}).get("pages",{}).values():
            thumb=pg.get("thumbnail",{}).get("source")
            if thumb:
                img=dl(thumb)
                if img: return img
    except: pass
    return None

def get_bg(name):
    nl=name.lower()
    for k,v in BIG_BG.items():
        if k in nl: return v
    return (10,22,10)

def make_img(h,a,hs,as_,lg,minute,scorer,h_id,a_id,player_name,espn_id):
    bg=get_bg(h)
    W,H=1080,1350
    img=Image.new("RGB",(W,H),bg)
    d=ImageDraw.Draw(img)
    try:
        fb=ImageFont.truetype("DejaVuSans-Bold.ttf", 95)
        fm=ImageFont.truetype("DejaVuSans-Bold.ttf", 48)
        fs=ImageFont.truetype("DejaVuSans-Bold.ttf", 36)
        fsmall=ImageFont.truetype("DejaVuSans.ttf", 30)
    except: fb=fm=fs=fsmall=ImageFont.load_default()

    # BRAND TOP 🟢
    d.rounded_rectangle([30,20,W-30,85], radius=20, fill=(0,255,100))
    d.text((50,30), f"Unfiltered Scores 🟢 • {lg}", font=fs, fill=(0,0,0))
    d.text((750,30), minute, font=fs, fill=(0,0,0))

    real_photo = get_real_scorer_photo(player_name, espn_id)
    if real_photo:
        real_photo=real_photo.resize((520,520))
        d.ellipse([270,110,810,650], fill=(255,255,255))
        img.paste(real_photo,(280,120),real_photo)

    def badge(tid,x):
        if not tid: return
        b=dl(f"https://a.espncdn.com/i/teamlogos/soccer/500/{tid}.png")
        if b:
            b=b.resize((180,180))
            img.paste(b,(x,160),b)
    badge(h_id,80)
    badge(a_id,820)

    d.text((60,400), h[:14].upper(), font=fm, fill=(255,255,255))
    d.text((800,400), a[:14].upper(), font=fm, fill=(255,255,255))

    d.rounded_rectangle([280,700,800,820], radius=30, fill=(255,255,255))
    d.text((340,720), f"{hs} - {as_}", font=fb, fill=(0,0,0))

    if scorer:
        for i,ln in enumerate(textwrap.wrap(scorer,40)[:3]):
            d.text((60,870+i*48), ln, font=fsmall, fill=(255,255,255))

    # BRAND BOTTOM 🟢
    d.rounded_rectangle([30,1240,W-30,1320], radius=20, fill=(0,255,100))
    d.text((50,1255), f"Unfiltered Scores 🟢 LIVE • {player_name}", font=fs, fill=(0,0,0))
    d.ellipse([1000,110,1050,160], fill=(0,255,100))

    path="/tmp/m.png"
    img.save(path)
    return path

def post(msg, path):
    try:
        url=f"https://graph.facebook.com/v20.0/{PAGE_ID}/photos"
        with open(path,"rb") as f:
            r=requests.post(url, data={"caption":msg,"access_token":PAGE_TOKEN}, files={"source":f}, timeout=15)
        print(f"POST {r.status_code}")
        return r.status_code==200
    except Exception as e:
        print(e); return False

def get_sb(lg):
    try:
        j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/scoreboard", timeout=4).json()
        evs=[]
        for ev in j.get("events",[]):
            ev["_code"]=lg; ev["_lname"]=NAMES.get(lg,lg); evs.append(ev)
        return evs
    except: return []

def get_sum(args):
    ev_id, code = args
    try:
        j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/summary?event={ev_id}", timeout=4).json()
        det=j.get("header",{}).get("competitions",[{}])[0].get("details",[]) or []
        lin=j.get("lineups",[]) or []
        return {"d":det,"l":lin}
    except: return {"d":[],"l":[]}

def main():
    st=load_state()
    all_ev=[]
    with ThreadPoolExecutor(max_workers=4) as ex:
        for lst in ex.map(get_sb, PRIORITY):
            all_ev.extend(lst)

    live=[e for e in all_ev if e["competitions"][0]["status"]["type"]["name"] in ["STATUS_IN_PROGRESS","STATUS_HALFTIME"]]
    if not live: live=all_ev[:12]
    print(f"V30 LIVE:{len(live)} - Unfiltered Scores 🟢")

    sums={}
    with ThreadPoolExecutor(max_workers=10) as ex:
        ids=[(e["id"], e["_code"]) for e in live]
        for e,s in zip(live, ex.map(get_sum, ids)):
            sums[e["id"]]=s

    posted=0
    for ev in live:
        ev_id=ev["id"]
        comp=ev["competitions"][0]
        status=comp["status"]["type"]["name"]
        short=comp["status"]["type"].get("shortDetail","")
        comps=comp["competitors"]
        try:
            h=next(x for x in comps if x["homeAway"]=="home")
            a=next(x for x in comps if x["homeAway"]=="away")
        except: continue
        hn,an=h["team"]["displayName"],a["team"]["displayName"]
        hid,aid=h["team"].get("id"),a["team"].get("id")
        hs,as_=str(h.get("score","0")), str(a.get("score","0"))
        lg=ev["_lname"]

        summ=sums.get(ev_id,{"d":[],"l":[]})
        details=summ["d"]
        m=re.search(r"(\d+)'", short); minute=int(m.group(1)) if m else 0

        # FIXED: Safe get for 'last' - no more KeyError
        last=st.get("last",{}).get(ev_id,"0-0")
        if status in ["STATUS_IN_PROGRESS","STATUS_HALFTIME"] and last!=f"{hs}-{as_}":
            if not (last=="0-0" and hs=="0" and as_=="0"):
                gid=f"{ev_id}_{hs}-{as_}"
                if gid not in st.get("goals",{}):
                    scorer_txt, pid, pname = f"GOAL! {hs}-{as_}", None, "Unknown"
                    for d in details[-5:]:
                        if "goal" in str(d.get("type","")).lower():
                            scorer_txt=d.get("text","")
                            pid=d.get("athlete",{}).get("id")
                            pname=d.get("athlete",{}).get("displayName","") or scorer_txt.split(" - ")[0][:20]
                            break
                    if not pname or pname=="Unknown":
                        if " - " in scorer_txt: pname=scorer_txt.split(" - ")[0].split("(")[0].strip()

                    img=make_img(hn,an,hs,as_,lg,f"{minute}' GOAL",scorer_txt,hid,aid,pname,pid)
                    if post(f"⚽ GOAL! {minute}' 🟢 {pname}\n\n{lg}\n{hn} {hs} - {as_} {an}\n\n{scorer_txt}\n\nUnfiltered Scores 🟢 LIVE\n#UnfilteredScores 🟢", img):
                        st.setdefault("goals",{})[gid]=1; posted+=1
        st.setdefault("last",{})[ev_id]=f"{hs}-{as_}"

    print(f"V30 DONE {posted} - Unfiltered Scores 🟢")
    save_state(st)

if __name__=="__main__": main()
