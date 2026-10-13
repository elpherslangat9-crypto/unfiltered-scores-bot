# V57 REAL IMAGE + NEWS ALL SOURCES - FIXED
import os,json,requests,re,random,time
import xml.etree.ElementTree as ET
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image,ImageDraw,ImageFont
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
PID=os.getenv("PAGE_ID")
TOK=os.getenv("PAGE_ACCESS_TOKEN") or os.getenv("FB_TOKEN")
FILE="posted_state.json"
EAT=ZoneInfo("Africa/Nairobi")
NAMES={"eng.1":"Premier League","eng.2":"Championship","esp.1":"LaLiga","fra.1":"Ligue 1","ita.1":"Serie A","ger.1":"Bundesliga","ken.1":"KPL","usa.1":"MLS","uefa.champions":"UCL","uefa.europa":"Europa"}
PR=["eng.1","eng.2","esp.1","fra.1","ita.1","ger.1","ken.1","usa.1","uefa.champions","uefa.europa"]
HASHTAGS={"Premier League":"#PremierLeague #EPL","KPL":"#KPL #FKFPL #KenyaFootball","MLS":"#MLS #Messi","UCL":"#UCL #ChampionsLeague","Europa":"#EuropaLeague"}
UK_TEAMS={"arsenal":"#Arsenal","manchester united":"#ManUtd"}
USA_TEAMS={"inter miami":"#InterMiami"}
def get_team_tags(hn,an):
    txt=(hn+" "+an).lower(); tags=[]
    for k,v in {**UK_TEAMS, **USA_TEAMS}.items():
        if k in txt: tags.append(v)
    return " ".join(tags[:2])
def load():
 d={"lineup":{},"goals":{},"ht":{},"ft":{},"last":{},"red":{},"kick":{},"news":[],"last_news_time":0,"pen_miss":{},"var":{},"pen_goal":{}}
 try:
  with open(FILE) as f:
   s=json.load(f)
   for k,v in d.items(): s.setdefault(k,v)
   return s
 except: return d
def save(s):
 with open(FILE,"w") as f: json.dump(s,f)
def dl(u):
 try:
  r=requests.get(u,timeout=8,headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36","Referer":"https://www.sofascore.com/"})
  if r.status_code==200 and len(r.content)>4000:
   return Image.open(BytesIO(r.content)).convert("RGBA")
 except: return None
def scorer_face(name,pid=None):
 if not name or len(name)<3: return None
 if name.lower() in ["lens","sporting cp","slavia prage","sabah fk"]: return None
 try:
  j=requests.get("https://api.sofascore.app/api/v1/search/all?q="+name,timeout=5,headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.sofascore.com/"}).json()
  for res in j.get("results",[]):
   if res.get("type")=="player":
    nid=res.get("entity",{}).get("id")
    if nid:
     im=dl("https://api.sofascore.app/api/v1/player/"+str(nid)+"/image")
     if im: return im
 except: pass
 return None
def get_real_game_image(eid,code,home,away):
    try:
        j=requests.get("https://site.api.espn.com/apis/site/v2/sports/soccer/"+code+"/summary?event="+str(eid),timeout=5).json()
        for pics in [j.get("header",{}).get("pics",[]), j.get("gameInfo",{}).get("pics",[])]:
            for p in pics:
                href=p.get("href") or p.get("url")
                if href:
                    im=dl(href)
                    if im and im.size[0]>500: return im
    except: pass
    try:
        j=requests.get("https://api.sofascore.app/api/v1/search/all?q="+home+" "+away,timeout=5,headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.sofascore.com/"}).json()
        for res in j.get("results",[])[:2]:
            if res.get("type")=="event":
                sid=res.get("entity",{}).get("id")
                if not sid: continue
                hj=requests.get("https://api.sofascore.app/api/v1/event/"+str(sid),timeout=5,headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.sofascore.com/"}).json()
                htid=hj.get("event",{}).get("homeTeam",{}).get("id")
                if htid:
                    im=dl("https://api.sofascore.app/api/v1/team/"+str(htid)+"/image")
                    if im: return im
    except: pass
    for tm_name in [home,away]:
        try:
            j=requests.get("https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t="+tm_name,timeout=5).json()
            tm=(j.get("teams") or [])[0] if j.get("teams") else None
            if tm:
                for k in ["strStadiumThumb","strTeamFanart1","strTeamFanart2","strTeamBanner"]:
                    url=tm.get(k)
                    if url and "http" in url:
                        im=dl(url)
                        if im and im.size[0]>400: return im
        except: pass
    return None
def get_sofascore_lineup(home,away):
    try:
        j=requests.get("https://api.sofascore.app/api/v1/search/all?q="+home+" "+away,timeout=5,headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.sofascore.com/"}).json()
        for res in j.get("results",[])[:2]:
            if res.get("type")=="event":
                sid=res.get("entity",{}).get("id")
                if not sid: continue
                lj=requests.get("https://api.sofascore.app/api/v1/event/"+str(sid)+"/lineups",timeout=5,headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.sofascore.com/"}).json()
                out=""
                for side in ["home","away"]:
                    tm=lj.get(side)
                    if not tm: continue
                    tname=tm.get("team",{}).get("name",side)
                    players=tm.get("players",[])[:11]
                    if len(players)>=3:
                        out+=tname+" XI:\n"
                        for p in players:
                            nm=p.get("player",{}).get("name","")
                            if nm: out+="- "+nm+"\n"
                        out+="\n"
                if len(out)>30: return out
    except: pass
    return ""
def fast_inc_all(home,away):
 g=[]; r=[]; pm=[]; pg=[]; var=[]
 try:
  j=requests.get("https://api.sofascore.app/api/v1/search/all?q="+home+" "+away,timeout=5,headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.sofascore.com/"}).json()
  for res in j.get("results",[])[:3]:
   if res.get("type")=="event":
    sid=res.get("entity",{}).get("id")
    if not sid: continue
    inc=requests.get("https://api.sofascore.app/api/v1/event/"+str(sid)+"/incidents",timeout=5,headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.sofascore.com/"}).json()
    for it in inc.get("incidents",[])[:30]:
     tp=it.get("incidentType",""); pn=it.get("player",{}).get("name",""); mn=it.get("time",0); pid=it.get("player",{}).get("id")
     ph=None
     if pid and pn:
         try: ph=dl("https://api.sofascore.app/api/v1/player/"+str(pid)+"/image")
         except: pass
     txt=str(it).lower()
     real_min = it.get("time",0)
     if isinstance(real_min,int) and real_min>0: mt=str(real_min)+"'"
     else: mt=str(mn)+"'"
     if tp=="goal":
         if pn and len(pn)>2 and pn.lower() not in [home.lower(),away.lower()]:
             g.append((pn,mt,ph,it))
     if tp=="card" and it.get("incidentClass")=="red": r.append((pn,mt,ph,it))
     if "penalty" in txt and "missed" in txt: pm.append((pn,mt,ph,it))
     elif tp=="penalty" or ("penalty" in txt and "goal" in txt): pg.append((pn,mt,ph,it))
     if "var" in txt: var.append((pn,mt,ph,it))
    if g or r or pm or pg or var: break
 except: pass
 return g,r,pm,pg,var
def get_hd_image(url):
 try:
  r=requests.get(url,timeout=8,headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
  m=re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',r.text,re.I)
  if m:
   u=m.group(1)
   if u.startswith("//"): u="https:"+u
   if "http" in u:
    im=dl(u)
    if im and im.size[0]>400: return im
  # Try twitter image
  m2=re.search(r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',r.text,re.I)
  if m2:
   u=m2.group(1)
   if u.startswith("//"): u="https:"+u
   im=dl(u)
   if im and im.size[0]>400: return im
 except: pass
 return None
def src_name(link):
 try: d=urlparse(link).netloc.lower(); return d.replace("www.","").split(".")[0].capitalize()
 except: return "Football News"
def bg_real(home,ground):
 W,H=1080,1350
 if ground:
  try:
   bg=ground.convert("RGB").resize((W,H),Image.LANCZOS)
   ov=Image.new("RGB",(W,H),(0,0,0))
   bg=Image.blend(bg,ov,0.4)
   return bg
  except: pass
 return None
def post(msg,path):
 try:
  url="https://graph.facebook.com/v20.0/"+str(PID)+"/photos"
  with open(path,"rb") as f:
   r=requests.post(url,data={"caption":msg,"access_token":TOK},files={"source":f},timeout=20)
  return r.status_code==200
 except: return False
def mk_img(h,a,sc,lg,top,bot,ground,face=None,red=False,orange=False):
 W,H=1080,1350
 bg=bg_real(h,ground)
 if bg is None and face is None: return None
 if bg is None and face is not None:
     try:
         bg=face.convert("RGB").resize((W,H),Image.LANCZOS)
         ov=Image.new("RGB",(W,H),(0,0,0))
         bg=Image.blend(bg,ov,0.5)
     except: bg=Image.new("RGB",(W,H),(12,24,12))
 d=ImageDraw.Draw(bg)
 try: fb=ImageFont.truetype("DejaVuSans-Bold.ttf",90); fs=ImageFont.truetype("DejaVuSans-Bold.ttf",34); fs2=ImageFont.truetype("DejaVuSans-Bold.ttf",28)
 except: fb=fs=fs2=ImageFont.load_default()
 col=(255,0,0) if red else (255,165,0) if orange else (0,255,100)
 d.rounded_rectangle([30,20,W-30,85],radius=20,fill=col)
 d.text((50,30),("Unfiltered "+lg+" "+top)[:44],font=fs,fill=(0,0,0) if not red else (255,255,255))
 if face:
  try:
   sf=face.resize((400,400),Image.LANCZOS); ms=Image.new("L",(400,400),0); ImageDraw.Draw(ms).ellipse([0,0,400,400],fill=255)
   bg.paste(sf,(340,130),ms,ms)
   d=ImageDraw.Draw(bg)
  except: pass
 d.rounded_rectangle([280,700,800,830],radius=30,fill=(255,255,255))
 d.text((340,720),sc,font=fb,fill=(0,0,0))
 d.rounded_rectangle([30,1240,W-30,1320],radius=20,fill=col)
 d.text((40,1252),bot[:56],font=fs2,fill=(0,0,0) if not red else (255,255,255))
 p="/tmp/m.png"; bg.save(p,quality=95); return p
def mk_news_img(real):
    W,H=1080,1350
    try:
        real=real.convert("RGB"); rw,rh=real.size
        max_h=H-90; ratio=min(W/rw,max_h/rh); new_w=int(rw*ratio); new_h=int(rh*ratio)
        fg=real.resize((new_w,new_h),Image.LANCZOS)
        bg=Image.new("RGB",(W,H),(0,0,0))
        bg.paste(fg,((W-new_w)//2,85+(max_h-new_h)//2))
    except: bg=Image.new("RGB",(W,H),(0,0,0))
    d=ImageDraw.Draw(bg,"RGBA")
    try: fs=ImageFont.truetype("DejaVuSans-Bold.ttf",36)
    except: fs=ImageFont.load_default()
    d.rounded_rectangle([15,15,W-15,80],radius=20,fill=(0,255,100))
    d.text((35,28),"Unfiltered Scores",font=fs,fill=(0,0,0))
    p="/tmp/news.png"; bg.save(p,quality=100); return p
def get_sb(lg):
 try:
  j=requests.get("https://site.api.espn.com/apis/site/v2/sports/soccer/"+lg+"/scoreboard",timeout=5).json()
  ev=[]
  for e in j.get("events",[]):
   e["_code"]=lg; e["_lname"]=NAMES.get(lg,lg); ev.append(e)
  return ev
 except: return []
def get_global_fast_live():
    ev=[]
    HEADERS={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36","Accept":"application/json","Referer":"https://www.sofascore.com/"}
    try:
        r=requests.get("https://api.sofascore.app/api/v1/sport/football/events/live",timeout=8,headers=HEADERS)
        if not r.text or len(r.text)<10: return ev
        try: j=r.json()
        except: return ev
        for e in j.get("events",[]):
            try:
                tour=e.get("tournament",{}).get("name","").lower()
                cat=e.get("tournament",{}).get("category",{}).get("name","").lower()
                combined=cat+" "+tour
                code=None; lname=None
                if "kenya" in combined: code="ken.1"; lname="KPL"
                elif "premier league" in combined and "england" in cat: code="eng.1"; lname="Premier League"
                elif "championship" in combined and "england" in cat: code="eng.2"; lname="Championship"
                elif "laliga" in combined or "la liga" in combined: code="esp.1"; lname="LaLiga"
                elif "ligue 1" in combined: code="fra.1"; lname="Ligue 1"
                elif "serie a" in combined: code="ita.1"; lname="Serie A"
                elif "bundesliga" in combined: code="ger.1"; lname="Bundesliga"
                elif "major league" in combined or "mls" in combined: code="usa.1"; lname="MLS"
                elif "champions league" in combined: code="uefa.champions"; lname="UCL"
                elif "europa league" in combined: code="uefa.europa"; lname="Europa"
                hn_raw=e.get("homeTeam",{}).get("name",""); an_raw=e.get("awayTeam",{}).get("name","")
                hn_low=hn_raw.lower(); an_low=an_raw.lower()
                if not code and any(x in hn_low+" "+an_low for x in ["gor mahia","leopards","tusker","shabana","kcb","bandari","homeboyz","muranga","city stars"]):
                    code="ken.1"; lname="KPL"
                if not code: continue
                hs=str(e.get("homeScore",{}).get("current",0)); as_=str(e.get("awayScore",{}).get("current",0))
                stype_raw=e.get("status",{}).get("type","")
                if stype_raw=="inprogress": stype="STATUS_IN_PROGRESS"
                elif stype_raw=="halftime": stype="STATUS_HALFTIME"
                elif stype_raw=="finished": stype="STATUS_FINAL"
                else: stype="STATUS_SCHEDULED"
                minute=e.get("time",{}).get("minute",0)
                ev.append({"id": "sofa_"+str(e.get('id')),"_code":code,"_lname":lname,"competitions":[{"status":{"type":{"name":stype,"shortDetail":str(minute)+"'"}},"competitors":[{"homeAway":"home","team":{"displayName":hn_raw},"score":hs},{"homeAway":"away","team":{"displayName":an_raw},"score":as_}],"date":""}]})
            except: pass
    except: pass
    return ev
def get_sum(ar):
 eid,code=ar
 try:
  j=requests.get("https://site.api.espn.com/apis/site/v2/sports/soccer/"+code+"/summary?event="+str(eid),timeout=5).json()
  return {"d":j.get("header",{}).get("competitions",[{}])[0].get("details",[]) or [],"l":j.get("lineups") or []}
 except: return {"d":[],"l":[]}
def lineup_txt(lins):
 if not lins: return ""
 out=""
 try:
  for tm in lins[:2]:
   tn=tm.get('team',{}).get('displayName',''); ro=tm.get('roster',[])
   if not ro or len(ro)<3: continue
   out+=tn+" XI:\n"
   for p in ro[:11]:
    nm=p.get('athlete',{}).get('displayName','')
    if nm: out+="- "+nm+"\n"
   out+="\n"
 except: return ""
 return out[:800]
# V57 NEWS ALL SOURCES WITH REAL PHOTOS ONLY
def fetch_news():
    BAD=["rugby","cricket","tennis","golf","boxing","darts","nfl","formula 1","netball","snooker","athletics","cycling","horse racing"]
    news=[]
    # 1. ESPN News - Real photos from ESPN API
    try:
        j=requests.get("https://site.api.espn.com/apis/site/v2/sports/soccer/news",timeout=8).json()
        for a in j.get("articles",[])[:15]:
            ttl=a.get("headline",""); ims=a.get("images",[]); img=ims[0].get("url") if ims else None
            if ttl and img and not any(b in ttl.lower() for b in BAD):
                dl_img=dl(img)
                if dl_img:
                    news.append({"title":ttl,"link":a.get("links",{}).get("web",{}).get("href",""),"img_url":img,"desc":a.get("description","")[:200],"source":"ESPN","hd":dl_img})
    except: pass
    # 2. Sky Sports RSS + Real OG Image
    try:
        r=requests.get("https://www.skysports.com/rss/12040",timeout=8)
        root=ET.fromstring(r.content)
        for item in root.findall(".//item")[:15]:
            ttl=item.findtext("title",""); lnk=item.findtext("link",""); desc=item.findtext("description","")[:200]
            if ttl and not any(b in (ttl+desc).lower() for b in BAD):
                hd=get_hd_image(lnk)
                if hd:
                    news.append({"title":ttl,"link":lnk,"img_url":None,"desc":desc,"source":"Sky Sports","hd":hd})
    except: pass
    # 3. BBC Sport RSS + Real OG Image
    try:
        r=requests.get("http://feeds.bbci.co.uk/sport/football/rss.xml",timeout=8)
        root=ET.fromstring(r.content)
        for item in root.findall(".//item")[:15]:
            ttl=item.findtext("title",""); lnk=item.findtext("link",""); desc=item.findtext("description","")[:200]
            if ttl and not any(b in (ttl+desc).lower() for b in BAD):
                hd=get_hd_image(lnk)
                if hd:
                    news.append({"title":ttl,"link":lnk,"img_url":None,"desc":desc,"source":"BBC Sport","hd":hd})
    except: pass
    # 4. Mozzart Sport Kenya + Real OG Image
    try:
        r=requests.get("https://www.mozzartsport.co.ke/football/",timeout=8)
        links=re.findall(r'<a[^>]+href="([^"]+football[^"]+)"[^>]*>([^<]{20,120})</a>',r.text)[:10]
        for href,ttl in links:
            if not href.startswith("http"): href="https://www.mozzartsport.co.ke"+href
            hd=get_hd_image(href)
            if hd:
                news.append({"title":ttl.strip()[:90],"link":href,"img_url":None,"desc":ttl[:200],"source":"Mozzart Sport Kenya","hd":hd})
    except: pass
    # 5. Pulse Sports KE + Real OG Image
    try:
        r=requests.get("https://www.pulsesports.co.ke/football/",timeout=8,headers={"User-Agent":"Mozilla/5.0"})
        found=re.findall(r'<a[^>]+href="([^"]+)"[^>]*>([^<]{20,100})</a>',r.text)
        for href,ttl in found[:15]:
            if any(x in ttl.lower() for x in ["gor","kpl","leopards","tusker","shabana","kenya","premier league","champions league","arsenal","man utd"]):
                if not href.startswith("http"): href="https://www.pulsesports.co.ke"+href
                hd=get_hd_image(href)
                if hd:
                    news.append({"title":ttl.strip()[:90],"link":href,"img_url":None,"desc":ttl[:200],"source":"Pulse Sports KE","hd":hd})
    except: pass
    # 6. Goal.com + Real OG Image
    try:
        r=requests.get("https://www.goal.com/en/lists",timeout=8,headers={"User-Agent":"Mozilla/5.0"})
        links=re.findall(r'<a[^>]+href="(/en[^"]+)"[^>]*>([^<]{20,120})</a>',r.text)[:10]
        for href,ttl in links:
            full="https://www.goal.com"+href
            hd=get_hd_image(full)
            if hd and not any(b in ttl.lower() for b in BAD):
                news.append({"title":ttl.strip()[:90],"link":full,"img_url":None,"desc":ttl[:200],"source":"Goal.com","hd":hd})
    except: pass
    print("NEWS TOTAL WITH REAL PHOTOS: "+str(len(news)))
    return news
def run_once(st):
 all_ev=[]
 with ThreadPoolExecutor(max_workers=10) as ex:
  for lst in ex.map(get_sb,PR): all_ev.extend(lst)
 try:
    fast_all=get_global_fast_live()
    if fast_all: all_ev.extend(fast_all)
 except: pass
 live=[e for e in all_ev if e["competitions"][0]["status"]["type"]["name"] in ["STATUS_IN_PROGRESS","STATUS_HALFTIME","STATUS_SCHEDULED","STATUS_FINAL"]]
 sums={}
 with ThreadPoolExecutor(max_workers=15) as ex:
  real_ids=[(e["id"],e["_code"]) for e in live if not str(e["id"]).startswith("sofa_")]
  temp={}
  for e,s in zip([ee for ee in live if not str(ee["id"]).startswith("sofa_")], ex.map(get_sum, real_ids)):
      temp[e["id"]]=s
  sums=temp
 posted=0
 for ev in live:
  eid=ev["id"]; code=ev["_code"]; comp=ev["competitions"][0]; status=comp["status"]["type"]["name"]; short=comp["status"]["type"].get("shortDetail","")
  comps=comp["competitors"]
  try: h=next(x for x in comps if x["homeAway"]=="home"); a=next(x for x in comps if x["homeAway"]=="away")
  except: continue
  hn,an=h["team"]["displayName"],a["team"]["displayName"]; hs,as_=str(h.get("score","0")),str(a.get("score","0")); lg=ev["_lname"]
  base_tag=HASHTAGS.get(lg,"#LiveFootball"); team_tags=get_team_tags(hn,an)
  tag=(str(base_tag)+" "+str(team_tags)+" #ViralFootball").strip()
  if lg=="KPL": tag="#KPL #FKFPL #KenyaFootball #AfricanFootball #ViralKE"
  summ=sums.get(eid,{"d":[],"l":[]}); details=summ["d"]; lins=summ["l"]
  m=re.search(r"(\d+)'",short); minute=int(m.group(1)) if m else 0
  ground=get_real_game_image(eid if not str(eid).startswith("sofa_") else "0",code,hn,an)
  try:
   ds=comp.get("date",""); dt=datetime.fromisoformat(ds.replace("Z","+00:00")).astimezone(EAT) if ds else datetime.now(EAT)
   df=dt.strftime("%a %d %b %Y"); tf=dt.strftime("%I:%M %p"); hrs=(dt - datetime.now(EAT)).total_seconds()/3600
  except: df=tf=""; hrs=0
  if status=="STATUS_SCHEDULED" and eid not in st.get("lineup",{}):
   if hrs<=2.5 and hrs>=-0.5:
    txt=lineup_txt(lins)
    if not txt or len(txt)<30: txt=get_sofascore_lineup(hn,an)
    i
