# bot.py V39 FINAL - FIXED INDENT - ALL FEATURES
import os, json, requests, re, xml.etree.ElementTree as ET, random, time
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

PAGE_ID=os.getenv("PAGE_ID")
PAGE_TOKEN=os.getenv("PAGE_ACCESS_TOKEN")
STATE_FILE="posted_state.json"
EAT=ZoneInfo("Africa/Nairobi")

NAMES={"eng.1":"Premier League","esp.1":"La Liga","uefa.champions":"UCL","ken.1":"KPL","ita.1":"Serie A","ger.1":"Bundesliga","eng.2":"Championship"}
PRIORITY=["eng.1","eng.2","esp.1","uefa.champions","ita.1","ger.1","ken.1"]
BIG_BG={"real madrid":(255,255,255),"barcelona":(20,20,120),"man city":(108,171,223),"arsenal":(239,1,7),"liverpool":(200,16,46),"chelsea":(3,70,148),"man utd":(218,0,0),"bayern":(220,5,45),"psg":(0,38,84),"villarreal":(255,223,0),"napoli":(0,70,160),"coventry":(0,120,180),"newcastle":(0,0,0)}

def load_state():
    default={"lineup":{},"goals":{},"ht":{},"ft":{},"last":{},"red":{},"pen":{},"news":[],"last_news_time":0}
    try:
        with open(STATE_FILE) as f:
            s=json.load(f)
            for k,v in default.items():
                s.setdefault(k,v)
            return s
    except:
        return default

def save_state(s):
    with open(STATE_FILE,"w") as f:
        json.dump(s,f)

def dl(url):
    try:
        r=requests.get(url, timeout=8, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code==200 and len(r.content)>4000:
            return Image.open(BytesIO(r.content)).convert("RGBA")
    except:
        return None
    return None

def get_real_scorer_photo(player_name, espn_id=None):
    if not player_name:
        return None
    if espn_id:
        im=dl(f"https://a.espncdn.com/i/headshots/soccer/players/full/{espn_id}.png")
        if im:
            return im
    try:
        s=requests.get(f"https://api.sofascore.app/api/v1/search/all?q={player_name}", timeout=5, headers={"User-Agent":"Mozilla/5.0"}).json()
        for res in s.get("results",[]):
            if res.get("type")=="player":
                pid=res.get("entity",{}).get("id")
                if pid:
                    im=dl(f"https://api.sofascore.app/api/v1/player/{pid}/image")
                    if im:
                        return im
    except:
        pass
    return None

def get_real_match_photo(ev_id, code, home, away):
    try:
        j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/summary?event={ev_id}", timeout=4).json()
        pics=j.get("header",{}).get("pics") or []
        if pics:
            href=pics[0].get("href")
            if href:
                im=dl(href)
                if im:
                    return im
    except:
        pass
    return None

def get_fast_incidents_from_sofa(home, away):
    goals=[]; reds=[]; pens=[]
    try:
        s=requests.get(f"https://api.sofascore.app/api/v1/search/all?q={home} {away}", timeout=4, headers={"User-Agent":"Mozilla/5.0"}).json()
        for res in s.get("results",[])[:3]:
            if res.get("type")=="event":
                eid=res.get("entity",{}).get("id")
                if not eid:
                    continue
                inc=requests.get(f"https://api.sofascore.app/api/v1/event/{eid}/incidents", timeout=4, headers={"User-Agent":"Mozilla/5.0"}).json()
                for incd in inc.get("incidents",[]):
                    itype=incd.get("incidentType","")
                    pname=incd.get("player",{}).get("name","")
                    minute=incd.get("time",0)
                    pid=incd.get("player",{}).get("id")
                    photo=None
                    if pid:
                        photo=dl(f"https://api.sofascore.app/api/v1/player/{pid}/image")
                    if itype=="goal":
                        goals.append((pname, f"{minute}'", photo, incd))
                    elif itype=="card" and incd.get("incidentClass")=="red":
                        reds.append((pname, f"{minute}'", photo))
                if goals or reds:
                    break
    except:
        pass
    return goals, reds, pens

def get_source_name(link):
    try:
        domain=urlparse(link).netloc.lower()
        if "skysports" in domain:
            return "Sky Sports"
        if "bbc" in domain:
            return "BBC Sport"
        if "espn" in domain:
            return "ESPN"
        if "goal.com" in domain:
            return "Goal.com"
        if "marca" in domain:
            return "Marca"
        return domain.replace("www.","").split(".")[0].capitalize()
    except:
        return "Football News"

def make_news_img_CLEAR(real_img):
    W,H=1080,1350
    try:
        real_img=real_img.convert("RGB")
        real_img=ImageEnhance.Sharpness(real_img).enhance(1.6)
        real_img=ImageEnhance.Contrast(real_img).enhance(1.15)
        rw,rh=real_img.size
        ratio=max(W/rw, H/rh)
        new_size=(int(rw*ratio), int(rh*ratio))
        bg=real_img.resize(new_size, Image.LANCZOS)
        left=(new_size[0]-W)//2
        top=(new_size[1]-H)//2
        bg=bg.crop((left, top, left+W, top+H))
    except:
        bg=real_img.resize((W,H), Image.LANCZOS)
    d=ImageDraw.Draw(bg, "RGBA")
    try:
        fs=ImageFont.truetype("DejaVuSans-Bold.ttf",36)
    except:
        fs=ImageFont.load_default()
    d.rounded_rectangle([15,15,W-15,80], radius=20, fill=(0,255,100))
    d.text((35,28), "Unfiltered Scores - BREAKING", font=fs, fill=(0,0,0))
    path="/tmp/news.png"
    bg.save(path, quality=100, subsampling=0)
    return path

def post(msg, path):
    try:
        url=f"https://graph.facebook.com/v20.0/{PAGE_ID}/photos"
        with open(path,"rb") as f:
            r=requests.post(url, data={"caption":msg,"access_token":PAGE_TOKEN}, files={"source":f}, timeout=20)
        print(f"POST {r.status_code}")
        return r.status_code==200
    except Exception as e:
        print(e)
        return False

def get_bg(name):
    nl=name.lower()
    for k,v in BIG_BG.items():
        if k in nl:
            return v
    return (12,24,12)

def make_lineup_img_clean(home, away, hid, aid, lg, date_str, time_str, real_ground):
    W,H=1080,1350
    if real_ground:
        try:
            bg=real_ground.resize((W,H), Image.LANCZOS)
            overlay=Image.new("RGBA",(W,H),(0,0,0,120))
            bg=Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
        except:
            bg=Image.new("RGB",(W,H),get_bg(home))
    else:
        bg=Image.new("RGB",(W,H),get_bg(home))
    d=ImageDraw.Draw(bg)
    try:
        fb=ImageFont.truetype("DejaVuSans-Bold.ttf",88)
        fm=ImageFont.truetype("DejaVuSans-Bold.ttf",42)
        fs=ImageFont.truetype("DejaVuSans-Bold.ttf",32)
    except:
        fb=fm=fs=ImageFont.load_default()
    d.rounded_rectangle([30,20,W-30,85], radius=20, fill=(0,255,100))
    d.text((50,30), f"Unfiltered Scores - {lg}", font=fs, fill=(0,0,0))
    d.text((780,30), "LINEUP", font=fs, fill=(0,0,0))
    def badge(tid,x,y):
        if not tid:
            return
        b=dl(f"https://a.espncdn.com/i/teamlogos/soccer/500/{tid}.png")
        if b:
            b=b.resize((260,260), Image.LANCZOS)
            bg.paste(b,(x,y),b)
    badge(hid,140,160)
    badge(aid,680,160)
    d.text((90,450), home.upper()[:16], font=fm, fill=(255,255,255))
    d.text((670,450), away.upper()[:16], font=fm, fill=(255,255,255))
    d.rounded_rectangle([360,600,720,680], radius=30, fill=(255,255,255))
    d.text((430,618), "VS", font=fb, fill=(0,0,0))
    d.text((250,760), f"{date_str}", font=fm, fill=(255,255,255))
    d.text((250,820), f"{time_str} EAT", font=fm, fill=(0,255,100))
    d.rounded_rectangle([30,1240,W-30,1320], radius=20, fill=(0,255,100))
    d.text((50,1255), f"Unfiltered Scores - {home} vs {away}", font=fs, fill=(0,0,0))
    path="/tmp/m.png"
    bg.save(path, quality=100)
    return path

def make_live_img(home, away, hid, aid, score, lg, top, bottom, real_ground, face=None):
    W,H=1080,1350
    if real_ground:
        try:
            bg=real_ground.resize((W,H), Image.LANCZOS)
            overlay=Image.new("RGBA",(W,H),(0,0,0,110))
            bg=Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
        except:
            bg=Image.new("RGB",(W,H),get_bg(home))
    else:
        bg=Image.new("RGB",(W,H),get_bg(home))
    d=ImageDraw.Draw(bg)
    try:
        fb=ImageFont.truetype("DejaVuSans-Bold.ttf",95)
        fm=ImageFont.truetype("DejaVuSans-Bold.ttf",48)
        fs=ImageFont.truetype("DejaVuSans-Bold.ttf",36)
    except:
        fb=fm=fs=ImageFont.load_default()
    d.rounded_rectangle([30,20,W-30,85], radius=20, fill=(0,255,100))
    d.text((50,30), f"Unfiltered Scores - {lg}", font=fs, fill=(0,0,0))
    d.text((750,30), top[:18], font=fs, fill=(255,255,255))
    if face:
        try:
            sf=face.resize((420,420), Image.LANCZOS)
            mask=Image.new("L",(420,420),0)
            ImageDraw.Draw(mask).ellipse([0,0,420,420], fill=255)
            bg.paste(sf,(330,140),mask)
            d.ellipse([330,140,750,560], outline=(0,255,100), width=6)
        except:
            pass
    else:
        def badge2(tid,x):
            if not tid:
                return
            b=dl(f"https://a.espncdn.com/i/teamlogos/soccer/500/{tid}.png")
            if b:
                b=b.resize((180,180), Image.LANCZOS)
                bg.paste(b,(x,200),b)
        badge2(hid,80)
        badge2(aid,820)
        d.text((60,450), home[:14].upper(), font=fm, fill=(255,255,255))
        d.text((800,450), away[:14].upper(), font=fm, fill=(255,255,255))
    d.rounded_rectangle([280,700,800,820], radius=30, fill=(255,255,255))
    d.text((340,720), score, font=fb, fill=(0,0,0))
    d.rounded_rectangle([30,1240,W-30,1320], radius=20, fill=(0,255,100))
    d.text((50,1255), bottom[:52], font=fs, fill=(0,0,0))
    path="/tmp/m.png"
    bg.save(path, quality=100)
    return path

def make_red_card_img(home, away, hid, aid, score, lg, player_name, minute, face, real_ground):
    W,H=1080,1350
    if real_ground:
        try:
            bg=real_ground.resize((W,H), Image.LANCZOS)
            overlay=Image.new("RGBA",(W,H),(0,0,0,110))
            bg=Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
        except:
            bg=Image.new("RGB",(W,H),(12,12,12))
    else:
        bg=Image.new("RGB",(W,H),(12,12,12))
    d=ImageDraw.Draw(bg)
    try:
        fb=ImageFont.truetype("DejaVuSans-Bold.ttf",90)
        fm=ImageFont.truetype("DejaVuSans-Bold.ttf",44)
        fs=ImageFont.truetype("DejaVuSans-Bold.ttf",34)
    except:
        fb=fm=fs=ImageFont.load_default()
    d.rounded_rectangle([30,20,W-30,85], radius=20, fill=(255,0,0))
    d.text((50,30), f"RED CARD - {lg}", font=fs, fill=(255,255,255))
    d.text((780,30), minute, font=fs, fill=(255,255,255))
    if face:
        try:
            sf=face.resize((380,380), Image.LANCZOS)
            mask=Image.new("L",(380,380),0)
            ImageDraw.Draw(mask).ellipse([0,0,380,380], fill=255)
            bg.paste(sf,(350,160),mask)
            d.ellipse([350,160,730,540], outline=(255,0,0), width=6)
        except:
            pass
    d.rounded_rectangle([30,600,W-30,760], radius=25, fill=(255,0,0))
    d.text((50,620), player_name[:30].upper(), font=fm, fill=(255,255,255))
    d.text((50,670), f"{minute} - RED CARD", font=fs, fill=(255,255,255))
    d.rounded_rectangle([280,780,800,880], radius=30, fill=(255,255,255))
    d.text((340,800), score, font=fb, fill=(0,0,0))
    d.text((280,900), f"{home} vs {away}", font=fm, fill=(255,255,255))
    d.rounded_rectangle([30,1240,W-30,1320], radius=20, fill=(255,0,0))
    d.text((50,1255), f"Unfiltered Scores - RED CARD {player_name}", font=fs, fill=(255,255,255))
    path="/tmp/m.png"
    bg.save(path, quality=100)
    return path

def make_ht_img_with_scorer(home, away, hid, aid, score, lg, scorers_list, real_ground):
    W,H=1080,1350
    if real_ground:
        try:
            bg=real_ground.resize((W,H), Image.LANCZOS)
            overlay=Image.new("RGBA",(W,H),(0,0,0,115))
            bg=Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
        except:
            bg=Image.new("RGB",(W,H),get_bg(home))
    else:
        bg=Image.new("RGB",(W,H),get_bg(home))
    d=ImageDraw.Draw(bg)
    try:
        fb=ImageFont.truetype("DejaVuSans-Bold.ttf",90)
        fm=ImageFont.truetype("DejaVuSans-Bold.ttf",42)
        fs=ImageFont.truetype("DejaVuSans-Bold.ttf",32)
    except:
        fb=fm=fs=ImageFont.load_default()
    d.rounded_rectangle([30,20,W-30,85], radius=20, fill=(0,255,100))
    d.text((50,30), f"Unfiltered Scores - {lg}", font=fs, fill=(0,0,0))
    d.text((800,30), "HT", font=fs, fill=(0,0,0))
    def badge(tid,x,y):
        b=dl(f"https://a.espncdn.com/i/teamlogos/soccer/500/{tid}.png")
        if b:
            b=b.resize((220,220), Image.LANCZOS)
            bg.paste(b,(x,y),b)
    badge(hid,120,140)
    badge(aid,740,140)
    d.text((90,390), home.upper()[:15], font=fm, fill=(255,255,255))
    d.text((700,390), away.upper()[:15], font=fm, fill=(255,255,255))
    d.rounded_rectangle([320,470,760,570], radius=30, fill=(255,255,255))
    d.text((380,485), score, font=fb, fill=(0,0,0))
    y=620
    for i in range(min(4,len(scorers_list))):
        name, minute, photo = scorers_list[i][0], scorers_list[i][1], scorers_list[i][2]
        if photo:
            try:
                p=photo.resize((110,110), Image.LANCZOS)
                mask=Image.new("L",(110,110),0)
                ImageDraw.Draw(mask).ellipse([0,0,110,110], fill=255)
                bg.paste(p,(70, y+i*135), mask)
            except:
                pass
        d.text((200, y+15+i*135), f"{name} {minute}", font=fm, fill=(255,255,255))
    d.rounded_rectangle([30,1240,W-30,1320], radius=20, fill=(0,255,100))
    d.text((50,1255), f"Unfiltered Scores - HT {score} - {home} vs {away}", font=fs, fill=(0,0,0))
    path="/tmp/m.png"
    bg.save(path, quality=100)
    return path

def get_sb(lg):
    try:
        j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/scoreboard", timeout=4).json()
        evs=[]
        for ev in j.get("events",[]):
            ev["_code"]=lg
            ev["_lname"]=NAMES.get(lg,lg)
            evs.append(ev)
        return evs
    except:
        return []

def get_sum(args):
    ev_id, code=args
    try:
        j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/summary?event={ev_id}", timeout=5).json()
        det=j.get("header",{}).get("competitions",[{}])[0].get("details",[]) or []
        line=j.get("lineups") or j.get("rosters") or []
        return {"d":det,"l":line}
    except:
        return {"d":[],"l":[]}

def get_lineup_text(lineups):
    if not lineups:
        return ""
    out=""
    try:
        for team in lineups[:2]:
            tname=team.get('team',{}).get('displayName','') or team.get('team',{}).get('name','')
            roster=team.get('roster',[]) or team.get('athletes',[])
            if not roster or len(roster)<7:
                return ""
            out+=f" {tname} XI:\n"
            for p in roster[:11]:
                name=p.get('athlete',{}).get('displayName','') or p.get('displayName','')
                if name:
                    out+=f"- {name}\n"
            out+="\n"
    except:
        return ""
    if "-" not in out:
        return ""
    return out[:600]

RSS_FEEDS=["https://feeds.bbci.co.uk/sport/football/rss.xml","https://www.skysports.com/rss/0,20514,11095,00.xml","https://www.goal.com/feeds/en/news","https://e00-marca.uecdn.es/rss/futbol/en.xml"]

def fetch_rss_news():
    news=[]
    for rss in RSS_FEEDS:
        try:
            r=requests.get(rss, timeout=6, headers={"User-Agent":"Mozilla/5.0"})
            root=ET.fromstring(r.content)
            for item in root.findall(".//item")[:5]:
                title=item.findtext("title","") or ""
                link=item.findtext("link","") or ""
                desc=item.findtext("description","") or ""
                img=None
                enc=item.find("enclosure")
                if enc is not None:
                    img=enc.get("url")
                if not img:
                    m=re.search(r'<img[^>]+src="([^"]+)"', desc)
                    if m:
                        img=m.group(1)
                if title and img:
                    news.append({"title":title.strip(),"link":link,"img":img,"desc":re.sub('<[^<]+?>','',desc)[:200]})
        except:
            continue
    return news

def fetch_espn_news():
    news=[]
    try:
        j=requests.get("https://site.api.espn.com/apis/site/v2/sports/soccer/news", timeout=6).json()
        for a in j.get("articles",[])[:8]:
            title=a.get("headline","")
            link=a.get("links",{}).get("web",{}).get("href","")
            imgs=a.get("images",[])
            img=imgs[0].get("url") if imgs else None
            if title and img:
                news.append({"title":title,"link":link,"img":img,"desc":a.get("description","")[:200]})
    except:
        pass
    return news

def run_once(st):
    all_ev=[]
    with ThreadPoolExecutor(max_workers=7) as ex:
        for lst in ex.map(get_sb, PRIORITY):
            all_ev.extend(lst)
    live=[e for e in all_ev if e["competitions"][0]["status"]["type"]["name"] in ["STATUS_IN_PROGRESS","STATUS_HALFTIME","STATUS_SCHEDULED","STATUS_FINAL"]]
    sums={}
    with ThreadPoolExecutor(max_workers=12) as ex:
        ids=[(e["id"], e["_code"]) for e in live]
        for e,s in zip(live, ex.map(get_sum, ids)):
            sums[e["id"]]=s
    posted=0
    for ev in live:
        ev_id=ev["id"]
        code=ev["_code"]
        comp=ev["competitions"][0]
        status=comp["status"]["type"]["name"]
        short=comp["status"]["type"].get("shortDetail","")
        comps=comp["competitors"]
        try:
            h=next(x for x in comps if x["homeAway"]=="home")
            a=next(x for x in comps if x["homeAway"]=="away")
        except:
            continue
        hn,an=h["team"]["displayName"],a["team"]["displayName"]
        hid,aid=h["team"].get("id"),a["team"].get("id")
        hs,as_=str(h.get("score","0")),str(a.get("score","0"))
        lg=ev["_lname"]
        summ=sums.get(ev_id,{"d":[],"l":[]})
        details=summ["d"]
        lineups=summ["l"]
        m=re.search(r"(\d+)'", short)
        minute=int(m.group(1)) if m else 0
        real_ground=get_real_match_photo(ev_id, code, hn, an)
        try:
            dt_str=comp.get("date","")
            dt=datetime.fromisoformat(dt_str.replace("Z","+00:00")).astimezone(EAT)
            date_fmt=dt.strftime("%a %d %b %Y")
            time_fmt=dt.strftime("%I:%M %p")
            hours_until=(dt - datetime.now(EAT)).total_seconds()/3600
        except:
            date_fmt=time_fmt=""
            hours_until=999

        if status=="STATUS_SCHEDULED" and ev_id not in st.get("lineup",{}):
            if hours_until <= 2.5 and hours_until >= -0.5:
                txt=get_lineup_text(lineups)
                if txt and len(txt)>30:
                    img=make_lineup_img_clean(hn,an,hid,aid,lg,date_fmt,time_fmt,real_ground)
                    if post(f"LINEUP - {lg}\n\n{hn} vs {an}\n\n{date_fmt} - {time_fmt} EAT\n\n{txt}Unfiltered Scores\n#UnfilteredScores", img):
                        st.setdefault("lineup",{})[ev_id]=1
                        posted+=1

        fast_goals, fast_reds, fast_pens = get_fast_incidents_from_sofa(hn,an)

        last=st.get("last",{}).get(ev_id,"0-0")
        if status in ["STATUS_IN_PROGRESS","STATUS_HALFTIME"] and last!=f"{hs}-{as_}":
            if not (last=="0-0" and hs=="0" and as_=="0"):
                gid=f"{ev_id}_{hs}-{as_}"
                if gid not in st.get("goals",{}):
                    scorer_txt,pid,pname="",None,""
                    for d in details[-6:]:
                        if "goal" in str(d.get("type","")).lower() or "Goal" in str(d.get("text","")):
                        scorer_txt=d.get("text","")
                        pid=d.get("athlete",{}).get("id")
                        pname=d.get("athlete",{}).get("displayName","")
                        break
                face=None
                minute_txt=f"{minute}'"
                is_pen=False
                if fast_goals:
                    pname_ft, minute_ft, face_ft, incd = fast_goals[-1]
                    if pname_ft:
                        pname=pname_ft
                    minute_txt=minute_ft
                    face=face_ft
                    if incd and "penalty" in str(incd).lower():
                        is_pen=True
                if not face and pname:
                    face=get_real_scorer_photo(pname,pid)
                if not pname:
                    pname=f"{hn}"
                label="PENALTY GOAL" if is_pen else f"{minute_txt} GOAL"
                img=make_live_img(hn,an,hid,aid,f"{hs}-{as_}",lg,label,f"Unfiltered Scores - {label} {pname}",real_ground,face)
                if post(f"GOAL! {label}! {minute_txt} - {pname}\n\n{lg}\n{hn} {hs} - {as_} {an}\n\n{scorer_txt or f'{pname} scores!'}\n\nUnfiltered Scores LIVE\n#UnfilteredScores", img):
                    st.setdefault("goals",{})[gid]=1
                    posted+=1
        st.setdefault("last",{})[ev_id]=f"{hs}-{as_}"

        for pname_red, minute_red, face_red in fast_reds:
            rid=f"{ev_id}_red_{pname_red}_{minute_red}"
            if rid not in st.get("red",{}):
                if not face_red:
                    face_red=get_real_scorer_photo(pname_red)
                img=make_red_card_img(hn,an,hid,aid,f"{hs}-{as_}",lg,pname_red,minute_red,face_red,real_ground)
                if post(f"RED CARD! {minute_red}\n\n{lg}\n{hn} {hs} - {as_} {an}\n\n{pname_red} sent off! {minute_red}\n\nUnfiltered Scores\n#UnfilteredScores", img):
                    st.setdefault("red",{})[rid]=1
                    posted+=1

        for d in details:
            txt=str(d.get("type","")).lower()+str(d.get("text","")).lower()
            if "red" in txt and "card" in txt:
                pname=d.get("athlete",{}).get("displayName","")
                pid=d.get("athlete",{}).get("id")
                minute_txt=d.get("clock",{}).get("displayValue","")
                rid=f"{ev_id}_red_espn_{pname}_{minute_txt}"
                if rid not in st.get("red",{}):
                    face=get_real_scorer_photo(pname,pid)
                    img=make_red_card_img(hn,an,hid,aid,f"{hs}-{as_}",lg,pname,minute_txt,face,real_ground)
                    if post(f"RED CARD! {minute_txt}\n\n{lg}\n{hn} {hs} - {as_} {an}\n\n{d.get('text','')}\n\nUnfiltered Scores", img):
                        st.setdefault("red",{})[rid]=1
                        posted+=1

        if status=="STATUS_HALFTIME" and ev_id not in st.get("ht",{}):
            scorers=fast_goals if fast_goals else []
            if not scorers:
                scorers=[]
                for d in details:
                    if "goal" in str(d.get("type","")).lower():
                        pname=d.get("athlete",{}).get("displayName","")
                        pid=d.get("athlete",{}).get("id")
                        mt=re.search(r"(\d+)'", d.get("clock",{}).get("displayValue","") or d.get("text",""))
                        minute_txt=mt.group(0) if mt else ""
                        face=get_real_scorer_photo(pname,pid)
                        scorers.append((pname, minute_txt, face, {}))
            img=make_ht_img_with_scorer(hn,an,hid,aid,f"{hs}-{as_}",lg,scorers,real_ground)
            names_txt="\n".join([f"{n} {m}" for n,m,ph,*_ in scorers]) or f"{hs}-{as_}"
            if post(f"HALFTIME\n\n{lg}\n{hn} {hs} - {as_} {an}\n\n{names_txt}\n\n{date_fmt} {time_fmt} EAT\n\nUnfiltered Scores\n#UnfilteredScores", img):
                st.setdefault("ht",{})[ev_id]=1
                posted+=1

        if status in ["STATUS_FINAL"] and ev_id not in st.get("ft",{}):
            img=make_live_img(hn,an,hid,aid,f"{hs}-{as_}",lg,"FT",f"Unfiltered Scores - FULL TIME",real_ground)
            if post(f"FULL TIME\n\n{lg}\n{hn} {hs} - {as_} {an}\n\n{date_fmt}\n\nUnfiltered Scores\n#UnfilteredScores", img):
                st.setdefault("ft",{})[ev_id]=1
                posted+=1
    return posted

def main():
    st=load_state()
    total=0
    for i in range(6):
        print(f"10sec loop {i+1}/6")
        total+=run_once(st)
        save_state(st)
        if i<5:
            time.sleep(10)

    now_ts=datetime.now().timestamp()
    if (now_ts - st.get("last_news_time",0)) > 1200:
        all_news=fetch_espn_news() + fetch_rss_news()
        random.shuffle(all_news)
        for n in all_news[:15]:
            title_raw=n["title"][:80]
            title_key=title_raw.strip().lower()
            existing_lowers=[x.lower() for x in st.get("news",[])]
            if title_key in existing_lowers:
                continue
            if any(title_key in ex or ex in title_key for ex in existing_lowers[-30:]):
                continue
            if "skysports.com/watch" in n["link"]:
                continue
            real=dl(n["img"])
            if not real:
                continue
            img=make_news_img_CLEAR(real)
            source_name=get_source_name(n["link"])
            cap=f"{n['title']}\n\n{n['desc']}\n\nSource: {source_name}\n\nUnfiltered Scores\n#UnfilteredScores #FootballNews"
            if post(cap, img):
                st.setdefault("news",[]).append(title_raw)
                if len(st["news"])>200:
                    st["news"]=st["news"][-200:]
                st["last_news_time"]=now_ts
                total+=1
                break
    print(f"V39 DONE {total}")
    save_state(st)

if __name__ == "__main__":
    main()
