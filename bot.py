# V54 GLOBAL FAST SEARCH - ALL LEAGUES + KPL NO-DELAY - 0 DELETION - ADDED ONLY
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
BIG={"real madrid":(255,255,255),"barcelona":(20,20,120),"man city":(108,171,223)}
HASHTAGS={"Premier League":"#PremierLeague #EPL","Championship":"#Championship","LaLiga":"#LaLiga","Serie A":"#SerieA","Bundesliga":"#Bundesliga","Ligue 1":"#Ligue1","KPL":"#KPL #FKFPL #KenyaFootball #AfricanFootball","MLS":"#MLS #Messi","UCL":"#UCL #ChampionsLeague","Europa":"#EuropaLeague"}
UK_TEAMS={"arsenal":"#Arsenal","manchester united":"#ManUtd","manchester city":"#ManCity","liverpool":"#Liverpool","chelsea":"#Chelsea"}
USA_TEAMS={"inter miami":"#InterMiami #Messi","la galaxy":"#LAGalaxy"}
def get_team_tags(hn,an):
    txt=(hn+" "+an).lower()
    tags=[]
    for d in [UK_TEAMS,USA_TEAMS]:
        for team,tag in d.items():
            if team in txt: tags.append(tag)
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
  r=requests.get(u,timeout=7,headers={"User-Agent":"Mozilla/5.0"})
  if r.status_code==200 and len(r.content)>3000:
   return Image.open(BytesIO(r.content)).convert("RGBA")
 except: return None
def scorer_face(name,pid=None):
 if pid:
  im=dl("https://a.espncdn.com/i/headshots/soccer/players/full/"+str(pid)+".png")
  if im: return im
 try:
  j=requests.get("https://api.sofascore.app/api/v1/search/all?q="+name,timeout=4,headers={"User-Agent":"Mozilla/5.0"}).json()
  for res in j.get("results",[]):
   if res.get("type")=="player":
    nid=res.get("entity",{}).get("id")
    if nid:
     im=dl("https://api.sofascore.app/api/v1/player/"+str(nid)+"/image")
     if im: return im
 except: pass
 return None
def real_photo_global(eid,code,home,away):
 try:
  j=requests.get("https://site.api.espn.com/apis/site/v2/sports/soccer/"+code+"/summary?event="+str(eid),timeout=4).json()
  for key in ["pics","header"]:
   pics=j.get("header",{}).get("pics",[]) if key=="header" else j.get("gameInfo",{}).get("pics",[])
   for p in pics:
    href=p.get("href") or p.get("url")
    if href:
     im=dl(href)
     if im and im.size[0]>400: return im
 except: pass
 for tm_name in [home,away,home.split()[-1],away.split()[-1]]:
  try:
   j=requests.get("https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t="+tm_name,timeout=4).json()
   tm=(j.get("teams") or [])[0] if j.get("teams") else None
   if tm:
    for k in ["strStadiumThumb","strTeamFanart1","strTeamFanart2","strTeamFanart3","strTeamThumb"]:
     url=tm.get(k)
     if url:
      im=dl(url)
      if im and im.size[0]>300: return im
  except: pass
 return None
def get_sofascore_lineup(home,away):
    try:
        j=requests.get("https://api.sofascore.app/api/v1/search/all?q="+home+" "+away,timeout=4,headers={"User-Agent":"Mozilla/5.0"}).json()
        for res in j.get("results",[])[:2]:
            if res.get("type")=="event":
                sid=res.get("entity",{}).get("id")
                if not sid: continue
                lj=requests.get("https://api.sofascore.app/api/v1/event/"+str(sid)+"/lineups",timeout=4,headers={"User-Agent":"Mozilla/5.0"}).json()
                if lj.get("home") or lj.get("away"):
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
  j=requests.get("https://api.sofascore.app/api/v1/search/all?q="+home+" "+away,timeout=4,headers={"User-Agent":"Mozilla/5.0"}).json()
  for res in j.get("results",[])[:3]:
   if res.get("type")=="event":
    sid=res.get("entity",{}).get("id")
    if not sid: continue
    inc=requests.get("https://api.sofascore.app/api/v1/event/"+str(sid)+"/incidents",timeout=4,headers={"User-Agent":"Mozilla/5.0"}).json()
    for it in inc.get("incidents",[]):
     tp=it.get("incidentType",""); pn=it.get("player",{}).get("name",""); mn=it.get("time",0); pid=it.get("player",{}).get("id")
     ph=None
     if pid:
         try: ph=dl("https://api.sofascore.app/api/v1/player/"+str(pid)+"/image")
         except: pass
     txt=str(it).lower()
     if tp=="goal": g.append((pn,str(mn)+"'",ph,it))
     if tp=="card" and it.get("incidentClass")=="red": r.append((pn,str(mn)+"'",ph,it))
     if "penalty" in txt and "missed" in txt: pm.append((pn,str(mn)+"'",ph,it))
     elif tp=="penalty" or ("penalty" in txt and "goal" in txt): pg.append((pn,str(mn)+"'",ph,it))
     if "var" in txt: var.append((pn,str(mn)+"'",ph,it))
    if g or r or pm or pg or var: break
 except: pass
 return g,r,pm,pg,var
def get_hd_image(url):
 try:
  r=requests.get(url,timeout=6,headers={"User-Agent":"Mozilla/5.0"})
  m=re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',r.text,re.I)
  if m:
   u=m.group(1)
   if u.startswith("//"): u="https:"+u
   im=dl(u)
   if im and im.size[0]>400: return im
 except: pass
 return None
def src_name(link):
 try:
  d=urlparse(link).netloc.lower()
  if "mozzart" in d: return "Mozzart Sport Kenya"
  if "tuko" in d: return "Tuko.co.ke"
  if "skysports" in d: return "Sky Sports"
  if "bbc" in d: return "BBC Sport"
  if "espn" in d: return "ESPN"
  if "goal" in d: return "Goal.com"
  if "nation" in d: return "Nation Africa"
  if "pulse" in d: return "Pulse Sports KE"
  return d.replace("www.","").split(".")[0].capitalize()
 except: return "Football News"
def get_bg(n):
 nl=n.lower()
 for k,v in BIG.items():
  if k in nl: return v
 return (12,24,12)
def bg_real(home,ground):
 W,H=1080,1350
 if ground:
  try:
   bg=ground.convert("RGB").resize((W,H),Image.LANCZOS)
   ov=Image.new("RGB",(W,H),(0,0,0))
   bg=Image.blend(bg,ov,0.35)
   return bg
  except: pass
 return Image.new("RGB",(W,H),get_bg(home))
def post(msg,path):
 try:
  url="https://graph.facebook.com/v20.0/"+str(PID)+"/photos"
  with open(path,"rb") as f:
   r=requests.post(url,data={"caption":msg,"access_token":TOK},files={"source":f},timeout=20)
  print("POST "+str(r.status_code))
  return r.status_code==200
 except Exception as e:
  print("POST ERR "+str(e))
  return False
def mk_img(h,a,sc,lg,top,bot,ground,face=None,red=False,orange=False):
 W,H=1080,1350
 bg=bg_real(h,ground)
 if red: bg=Image.new("RGB",(W,H),(50,10,10))
 if orange: bg=Image.new("RGB",(W,H),(60,35,5))
 d=ImageDraw.Draw(bg)
 try: fb=ImageFont.truetype("DejaVuSans-Bold.ttf",90); fs=ImageFont.truetype("DejaVuSans-Bold.ttf",34)
 except: fb=fs=ImageFont.load_default()
 col=(255,0,0) if red else (255,165,0) if orange else (0,255,100)
 d.rounded_rectangle([30,20,W-30,85],radius=20,fill=col)
 d.text((50,30),( "Unfiltered "+lg+" "+top)[:42],font=fs,fill=(0,0,0) if not red else (255,255,255))
 if face:
  try:
   sf=face.resize((380,380),Image.LANCZOS); ms=Image.new("L",(380,380),0); ImageDraw.Draw(ms).ellipse([0,0,380,380],fill=255)
   bg.paste(sf,(350,140),ms,ms)
  except: pass
 d=ImageDraw.Draw(bg)
 d.rounded_rectangle([280,700,800,820],radius=30,fill=(255,255,255)); d.text((340,720),sc,font=fb,fill=(0,0,0))
 d.rounded_rectangle([30,1240,W-30,1320],radius=20,fill=col)
 d.text((40,1252),bot[:54],font=fs,fill=(0,0,0) if not red else (255,255,255))
 p="/tmp/m.png"; bg.save(p,quality=95); return p
def mk_news_img(real):
    W,H=1080,1350
    try:
        real=real.convert("RGB"); rw,rh=real.size
        max_h=H-90; ratio=min(W/rw,max_h/rh); new_w=int(rw*ratio); new_h=int(rh*ratio)
        fg=real.resize((new_w,new_h),Image.LANCZOS)
        bg=Image.new("RGB",(W,H),(0,0,0))
        bg.paste(fg,((W-new_w)//2,85+(max_h-new_h)//2))
    except Exception:
        bg=Image.new("RGB",(W,H),(0,0,0))
    d=ImageDraw.Draw(bg,"RGBA")
    try: fs=ImageFont.truetype("DejaVuSans-Bold.ttf",36)
    except: fs=ImageFont.load_default()
    d.rounded_rectangle([15,15,W-15,80],radius=20,fill=(0,255,100))
    d.text((35,28),"Unfiltered Scores",font=fs,fill=(0,0,0))
    p="/tmp/news.png"; bg.save(p,quality=100); return p
def get_sb(lg):
 try:
  j=requests.get("https://site.api.espn.com/apis/site/v2/sports/soccer/"+lg+"/scoreboard",timeout=4).json()
  ev=[]
  for e in j.get("events",[]):
   e["_code"]=lg; e["_lname"]=NAMES.get(lg,lg); ev.append(e)
  return ev
 except: return []

# V54 NEW: GLOBAL FAST SEARCH FOR ALL LEAGUES - 15 SEC NO DELAY
def get_global_fast_live():
    ev=[]
    try:
        j=requests.get("https://api.sofascore.app/api/v1/sport/football/events/live",timeout=6,headers={"User-Agent":"Mozilla/5.0"}).json()
        all_live=j.get("events",[])
        print("SOFASCORE TOTAL LIVE: "+str(len(all_live)))
        for e in all_live:
            try:
                tour=e.get("tournament",{}).get("name","").lower()
                cat=e.get("tournament",{}).get("category",{}).get("name","").lower()
                cslug=e.get("tournament",{}).get("slug","").lower()
                combined=cat+" "+tour+" "+cslug
                # MAP TO YOUR CODES
                code=None; lname=None
                if "kenya" in combined or any(x in combined for x in ["fkf","kpl"]): code="ken.1"; lname="KPL"
                elif "premier league" in combined and "england" in cat: code="eng.1"; lname="Premier League"
                elif "championship" in combined and "england" in cat: code="eng.2"; lname="Championship"
                elif "laliga" in combined or ("la liga" in combined and "spain" in cat): code="esp.1"; lname="LaLiga"
                elif "ligue 1" in combined and "france" in cat: code="fra.1"; lname="Ligue 1"
                elif "serie a" in combined and "italy" in cat: code="ita.1"; lname="Serie A"
                elif "bundesliga" in combined and "germany" in cat: code="ger.1"; lname="Bundesliga"
                elif "major league soccer" in combined or "mls" in combined: code="usa.1"; lname="MLS"
                elif "champions league" in combined or "uefa champions" in combined: code="uefa.champions"; lname="UCL"
                elif "europa league" in combined: code="uefa.europa"; lname="Europa"
                # KPL extra team check
                hn_raw=e.get("homeTeam",{}).get("name",""); an_raw=e.get("awayTeam",{}).get("name","")
                hn_low=hn_raw.lower(); an_low=an_raw.lower()
                if not code and any(x in hn_low+" "+an_low for x in ["gor mahia","afc leopards","tusker","shabana","kcb","bandari","homeboyz","muranga seal","city stars","mara sugar","bidco","nairobi city"]):
                    code="ken.1"; lname="KPL"
                if not code: continue
                hn=hn_raw; an=an_raw
                hs=str(e.get("homeScore",{}).get("current",0)); as_=str(e.get("awayScore",{}).get("current",0))
                stype_raw=e.get("status",{}).get("type","")
                if stype_raw=="inprogress": stype="STATUS_IN_PROGRESS"
                elif stype_raw=="halftime": stype="STATUS_HALFTIME"
                elif stype_raw=="finished": stype="STATUS_FINAL"
                else: stype="STATUS_SCHEDULED"
                minute=e.get("time",{}).get("minute",0)
                ev.append({"id": "sofa_"+str(e.get('id')),"_code":code,"_lname":lname,"competitions":[{"status":{"type":{"name":stype,"shortDetail":str(minute)+"'"}},"competitors":[{"homeAway":"home","team":{"displayName":hn},"score":hs},{"homeAway":"away","team":{"displayName":an},"score":as_}],"date":""}]})
                print("FAST FOUND: "+lname+" "+hn+" vs "+an+" "+hs+"-"+as_)
            except: pass
    except Exception as ex:
        print("GLOBAL FAST ERR "+str(ex))
    print("GLOBAL FAST TOTAL: "+str(len(ev))+" games")
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
def fetch_kpl_news_extra():
    news=[]
    try:
        r=requests.get("https://www.pulsesports.co.ke/football/",timeout=6,headers={"User-Agent":"Mozilla/5.0"})
        for m in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>([^<]{20,100})</a>',r.text)[:10]:
            href,ttl=m
            if any(x in ttl.lower() for x in ["gor","kpl","leopards","tusker","shabana","kenya"]):
                if not href.startswith("http"): href="https://www.pulsesports.co.ke"+href
                hd=get_hd_image(href)
                if hd: news.append({"title":ttl.strip()[:90],"link":href,"img_url":None,"desc":ttl[:200],"source":"Pulse Sports KE","hd":hd})
    except: pass
    return news
def fetch_news():
    BAD=["rugby","cricket","tennis","golf","boxing","darts","nfl","formula 1","netball","snooker","athletics","cycling","horse racing"]
    news=[]
    try:
        j=requests.get("https://site.api.espn.com/apis/site/v2/sports/soccer/news",timeout=6).json()
        for a in j.get("articles",[])[:10]:
            ttl=a.get("headline",""); ims=a.get("images",[]); img=ims[0].get("url") if ims else None
            if ttl and img and not any(b in ttl.lower() for b in BAD):
                news.append({"title":ttl,"link":a.get("links",{}).get("web",{}).get("href",""),"img_url":img,"desc":a.get("description","")[:200],"source":"ESPN","hd":None})
    except: pass
    try:
        r=requests.get("https://www.skysports.com/rss/12040",timeout=6)
        root=ET.fromstring(r.content)
        for item in root.findall(".//item")[:12]:
            ttl=item.findtext("title",""); lnk=item.findtext("link",""); desc=item.findtext("description","")[:200]
            if ttl and not any(b in (ttl+desc).lower() for b in BAD):
                news.append({"title":ttl,"link":lnk,"img_url":None,"desc":desc,"source":"Sky Sports","hd":get_hd_image(lnk)})
    except: pass
    try:
        r=requests.get("http://feeds.bbci.co.uk/sport/football/rss.xml",timeout=6)
        root=ET.fromstring(r.content)
        for item in root.findall(".//item")[:10]:
            ttl=item.findtext("title",""); lnk=item.findtext("link",""); desc=item.findtext("description","")[:200]
            if ttl and not any(b in (ttl+desc).lower() for b in BAD):
                news.append({"title":ttl,"link":lnk,"img_url":None,"desc":desc,"source":"BBC Sport","hd":get_hd_image(lnk)})
    except: pass
    try:
        extra=fetch_kpl_news_extra()
        news.extend(extra)
    except: pass
    try:
        r=requests.get("https://www.mozzartsport.co.ke/football/",timeout=6)
        links=re.findall(r'<a[^>]+href="([^"]+football[^"]+)"[^>]*>([^<]{20,120})</a>',r.text)[:8]
        for href,ttl in links:
            if not href.startswith("http"): href="https://www.mozzartsport.co.ke"+href
            hd=get_hd_image(href)
            if hd: news.append({"title":ttl.strip()[:90],"link":href,"img_url":None,"desc":ttl[:200],"source":"Mozzart Sport Kenya","hd":hd})
    except: pass
    return news
def run_once(st):
 all_ev=[]
 with ThreadPoolExecutor(max_workers=10) as ex:
  for lst in ex.map(get_sb,PR): all_ev.extend(lst)
 # V54 GLOBAL FAST LANE FOR ALL LEAGUES
 try:
    fast_all=get_global_fast_live()
    if fast_all:
        all_ev.extend(fast_all)
 except Exception as ex:
    print("FAST ERR "+str(ex))
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
  tag=(str(base_tag)+" "+str(team_tags)+" #ViralFootball #Football #WorldFootball").strip()
  if lg=="KPL": tag="#KPL #FKFPL #KenyaFootball #AfricanFootball #GorMahia #TuskerFC #ViralKE"
  if lg=="MLS": tag="#MLS #Messi #InterMiami #USASoccer #ViralUSA"
  if lg in ["Premier League","Championship"]: tag="#PremierLeague #EPL #UKFootball #Arsenal #ManUtd #Chelsea #Liverpool #ViralUK"
  summ=sums.get(eid,{"d":[],"l":[]}); details=summ["d"]; lins=summ["l"]
  m=re.search(r"(\d+)'",short); minute=int(m.group(1)) if m else 0
  ground=real_photo_global(eid if not str(eid).startswith("sofa_") else "0",code,hn,an)
  try:
   ds=comp.get("date",""); dt=datetime.fromisoformat(ds.replace("Z","+00:00")).astimezone(EAT) if ds else datetime.now(EAT)
   df=dt.strftime("%a %d %b %Y"); tf=dt.strftime("%I:%M %p"); hrs=(dt - datetime.now(EAT)).total_seconds()/3600
  except: df=tf=""; hrs=0
  if status=="STATUS_SCHEDULED" and eid not in st.get("lineup",{}):
   if hrs<=2.5 and hrs>=-0.5:
    txt=lineup_txt(lins)
    if not txt or len(txt)<30: txt=get_sofascore_lineup(hn,an)
    if txt and len(txt)>30:
     bg=bg_real(hn,ground); d=ImageDraw.Draw(bg)
     try: fs=ImageFont.truetype("DejaVuSans-Bold.ttf",32)
     except: fs=ImageFont.load_default()
     d.rounded_rectangle([30,20,1050,85],radius=20,fill=(0,255,100)); d.text((50,30),"LINEUP "+lg,font=fs,fill=(0,0,0))
     p="/tmp/m.png"; bg.save(p,quality=90)
     cap_text = "LINEUP "+lg+"\n\n"+hn+" vs "+an+"\n\n"+df+" "+tf+" EAT\n\n"+txt+"\nWho wins? Comment! FOLLOW NOW!\n\n"+tag
     if post(cap_text,p):
      st.setdefault("lineup",{})[eid]=1; posted+=1
  if status=="STATUS_IN_PROGRESS" and eid not in st.get("kick",{}):
   if minute<=10:
    img=mk_img(hn,an,"0-0",lg,"KICK OFF","KICK OFF "+hn+" vs "+an,ground)
    cap_text = "KICK OFF! "+lg+"\n\n"+hn+" vs "+an+"\n\n"+df+" "+tf+" EAT\n\nPredict score!\n\n"+tag
    if post(cap_text,img):
     st.setdefault("kick",{})[eid]=1; posted+=1
  gl,rl,pml,pgl,varl=fast_inc_all(hn,an)
  last=st.get("last",{}).get(eid,"0-0")
  if status in ["STATUS_IN_PROGRESS","STATUS_HALFTIME"] and last!=hs+"-"+as_
