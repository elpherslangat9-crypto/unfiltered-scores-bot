# V51 FIXED GLOBAL - ALL PHOTO SOURCES WORLDWIDE + VIRAL - NO ERROR
import os,json,requests,re,random,time
import xml.etree.ElementTree as ET
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image,ImageDraw,ImageFont
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

PID=os.getenv("PAGE_ID")
TOK=os.getenv("PAGE_ACCESS_TOKEN")
FILE="posted_state.json"
EAT=ZoneInfo("Africa/Nairobi")

NAMES={
 "eng.1":"Premier League","eng.2":"Championship","esp.1":"LaLiga",
 "fra.1":"Ligue 1","ita.1":"Serie A","ger.1":"Bundesliga",
 "ken.1":"KPL","usa.1":"MLS","uefa.champions":"UCL","uefa.europa":"Europa"
}
PR=["eng.1","eng.2","esp.1","fra.1","ita.1","ger.1","ken.1","usa.1","uefa.champions","uefa.europa"]
BIG={"real madrid":(255,255,255),"barcelona":(20,20,120),"man city":(108,171,223)}

HASHTAGS={
 "Premier League":"#PremierLeague #EPL #UKFootball #EnglandFootball",
 "Championship":"#Championship #EFL #UKFootball",
 "LaLiga":"#LaLiga #Spain","Serie A":"#SerieA","Bundesliga":"#Bundesliga",
 "Ligue 1":"#Ligue1","KPL":"#KPL #FKFPL #KenyaFootball #AfricanFootball",
 "MLS":"#MLS #Messi #InterMiami #USASoccer","UCL":"#UCL #ChampionsLeague","Europa":"#EuropaLeague"
}
KPL_TEAMS=["gor mahia","afc leopards","tusker","shabana","kcb","bandari"]
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
  im=dl(f"https://a.espncdn.com/i/headshots/soccer/players/full/{pid}.png")
  if im: return im
 try:
  j=requests.get(f"https://api.sofascore.app/api/v1/search/all?q={name}",timeout=4,headers={"User-Agent":"Mozilla/5.0"}).json()
  for res in j.get("results",[]):
   if res.get("type")=="player":
    nid=res.get("entity",{}).get("id")
    if nid:
     im=dl(f"https://api.sofascore.app/api/v1/player/{nid}/image")
     if im: return im
 except: pass
 return None

def real_photo_global(eid,code,home,away):
 try:
  j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/summary?event={eid}",timeout=4).json()
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
   j=requests.get(f"https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t={tm_name}",timeout=4).json()
   tm=(j.get("teams") or [])[0] if j.get("teams") else None
   if tm:
    for k in ["strStadiumThumb","strTeamFanart1","strTeamFanart2","strTeamFanart3","strTeamThumb"]:
     url=tm.get(k)
     if url:
      im=dl(url)
      if im and im.size[0]>300: return im
  except: pass
 return None

def fast_inc_all(home,away):
 g=[]; r=[]; pm=[]; pg=[]; var=[]
 try:
  j=requests.get(f"https://api.sofascore.app/api/v1/search/all?q={home} {away}",timeout=4,headers={"User-Agent":"Mozilla/5.0"}).json()
  for res in j.get("results",[])[:3]:
   if res.get("type")=="event":
    sid=res.get("entity",{}).get("id")
    if not sid: continue
    inc=requests.get(f"https://api.sofascore.app/api/v1/event/{sid}/incidents",timeout=4,headers={"User-Agent":"Mozilla/5.0"}).json()
    for it in inc.get("incidents",[]):
     tp=it.get("incidentType",""); pn=it.get("player",{}).get("name",""); mn=it.get("time",0); pid=it.get("player",{}).get("id")
     ph=dl(f"https://api.sofascore.app/api/v1/player/{pid}/image") if pid else None
     txt=str(it).lower()
     if tp=="goal": g.append((pn,f"{mn}'",ph,it))
     if tp=="card" and it.get("incidentClass")=="red": r.append((pn,f"{mn}'",ph,it))
     if "penalty" in txt and "missed" in txt: pm.append((pn,f"{mn}'",ph,it))
     elif tp=="penalty" or "penalty" in txt and "goal" in txt: pg.append((pn,f"{mn}'",ph,it))
     if "var" in txt: var.append((pn,f"{mn}'",ph,it))
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
  url=f"https://graph.facebook.com/v20.0/{PID}/photos"
  with open(path,"rb") as f:
   r=requests.post(url,data={"caption":msg,"access_token":TOK},files={"source":f},timeout=20)
  return r.status_code==200
 except: return False

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
 d.text((50,30),f"Unfiltered {lg} {top}"[:42],font=fs,fill=(0,0,0) if not red else (255,255,255))
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
    try:
        fs=ImageFont.truetype("DejaVuSans-Bold.ttf",36)
    except:
        fs=ImageFont.load_default()
    d.rounded_rectangle([15,15,W-15,80],radius=20,fill=(0,255,100))
    d.text((35,28),"Unfiltered Scores",font=fs,fill=(0,0,0))
    p="/tmp/news.png"; bg.save(p,quality=100); return p

def get_sb(lg):
 try:
  j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/scoreboard",timeout=4).json()
  ev=[]
  for e in j.get("events",[]):
   e["_code"]=lg; e["_lname"]=NAMES.get(lg,lg); ev.append(e)
  return ev
 except: return []
def get_sum(ar):
 eid,code=ar
 try:
  j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/summary?event={eid}",timeout=5).json()
  return {"d":j.get("header",{}).get("competitions",[{}])[0].get("details",[]) or [],"l":j.get("lineups") or []}
 except: return {"d":[],"l":[]}
def lineup_txt(lins):
 if not lins: return ""
 out=""
 try:
  for tm in lins[:2]:
   tn=tm.get('team',{}).get('displayName',''); ro=tm.get('roster',[])
   if not ro or len(ro)<7: return ""
   out+=f"{tn} XI:\n"
   for p in ro[:11]:
    nm=p.get('athlete',{}).get('displayName','')
    if nm: out+=f"- {nm}\n"
   out+="\n"
 except: return ""
 return out[:600]

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
 live=[e for e in all_ev if e["competitions"][0]["status"]["type"]["name"] in ["STATUS_IN_PROGRESS","STATUS_HALFTIME","STATUS_SCHEDULED","STATUS_FINAL"]]
 sums={}
 with ThreadPoolExecutor(max_workers=15) as ex:
  ids=[(e["id"],e["_code"]) for e in live]
  for e,s in zip(live,ex.map(get_sum,ids)): sums[e["id"]]=s
 posted=0
 for ev in live:
  eid=ev["id"]; code=ev["_code"]; comp=ev["competitions"][0]; status=comp["status"]["type"]["name"]; short=comp["status"]["type"].get("shortDetail","")
  comps=comp["competitors"]
  try: h=next(x for x in comps if x["homeAway"]=="home"); a=next(x for x in comps if x["homeAway"]=="away")
  except: continue
  hn,an=h["team"]["displayName"],a["team"]["displayName"]; hs,as_=str(h.get("score","0")),str(a.get("score","0")); lg=ev["_lname"]
  base_tag=HASHTAGS.get(lg,"#LiveFootball"); team_tags=get_team_tags(hn,an)
  tag=f"{base_tag} {team_tags} #ViralFootball #Football #WorldFootball".strip()
  if lg=="KPL": tag="#KPL #FKFPL #KenyaFootball #AfricanFootball #GorMahia #TuskerFC #ViralKE"
  if lg=="MLS": tag="#MLS #Messi #InterMiami #USASoccer #ViralUSA"
  if lg in ["Premier League","Championship"]: tag="#PremierLeague #EPL #UKFootball #Arsenal #ManUtd #Chelsea #Liverpool #ViralUK"
  summ=sums.get(eid,{"d":[],"l":[]}); details=summ["d"]; lins=summ["l"]
  m=re.search(r"(\d+)'",short); minute=int(m.group(1)) if m else 0
  ground=real_photo_global(eid,code,hn,an)
  try:
   ds=comp.get("date",""); dt=datetime.fromisoformat(ds.replace("Z","+00:00")).astimezone(EAT)
   df=dt.strftime("%a %d %b %Y"); tf=dt.strftime("%I:%M %p"); hrs=(dt - datetime.now(EAT)).total_seconds()/3600
  except: df=tf=""; hrs=999
  if status=="STATUS_SCHEDULED" and eid not in st.get("lineup",{}):
   if hrs<=2.5 and hrs>=-0.5:
    txt=lineup_txt(lins)
    if txt and len(txt)>30:
     bg=bg_real(hn,ground); d=ImageDraw.Draw(bg)
     try: fs=ImageFont.truetype("DejaVuSans-Bold.ttf",32)
     except: fs=ImageFont.load_default()
     d.rounded_rectangle([30,20,1050,85],radius=20,fill=(0,255,100)); d.text((50,30),f"LINEUP {lg}",font=fs,fill=(0,0,0))
     p="/tmp/m.png"; bg.save(p,quality=90)
     if post(f"LINEUP {lg}\n\n{hn} vs {an}\n\n{df} {tf} EAT\n\n{txt}\nWho wins? Comment 👇 🔔 FOLLOW NOW!\n\n{tag}",p):
      st.setdefault("lineup",{})[eid]=1; posted+=1
  if status=="STATUS_IN_PROGRESS" and eid not in st.get("kick",{}):
   if minute<=3:
    img=mk_img(hn,an,"0-0",lg,"KICK OFF",f"KICK OFF {hn} vs {an}",ground)
    if post(f"🚨 KICK OFF! {lg}\n\n{hn} vs {an}\n\n{df} {tf} EAT\n\nPredict score 👇 🔔 FOLLOW!\n\n{tag}",img):
     st.setdefault("kick",{})[eid]=1; posted+=1
  gl,rl,pml,pgl,varl=fast_inc_all(hn,an)
  last=st.get("last",{}).get(eid,"0-0")
  if status in ["STATUS_IN_PROGRESS","STATUS_HALFTIME"] and last!=f"{hs}-{as_}":
   if not (last=="0-0" and hs=="0" and as_=="0"):
    gid=f"{eid}_{hs}-{as_}"
    if gid not in st.get("goals",{}):
     pname=""; pid=None
     for d in details[-6:]:
      if "goal" in str(d.get("type","")).lower():
       pname=d.get("athlete",{}).get("displayName",""); pid=d.get("athlete",{}).get("id"); break
     face=None; mt=f"{minute}'"; is_pen=False
     if gl:
      pn,mt,fc,it=gl[-1]
      if pn: pname=pn; face=fc
      if it and "penalty" in str(it).lower(): is_pen=True
     if not face and pname: face=scorer_face(pname,pid)
     if not pname: pname=hn
     label="PENALTY" if is_pen else f"{mt} GOAL"
     img=mk_img(hn,an,f"{hs}-{as_}",lg,label,f"{label} {pname}",ground,face)
     if post(f"🔥 GOAL! {label}! {mt} {pname}\n\n{lg}\n{hn} {hs}-{as_} {an}\n\nWho scores next? Comment 👇 🔔 FOLLOW NOW!\n\n{tag}",img):
      st.setdefault("goals",{})[gid]=1; posted+=1
  st.setdefault("last",{})[eid]=f"{hs}-{as_}"
  for pn,mt,fc,it in rl:
   rid=f"{eid}_red_{pn}_{mt}"
   if rid not in st.get("red",{}):
    if not fc: fc=scorer_face(pn)
    img=mk_img(hn,an,f"{hs}-{as_}",lg,f"RED {mt}",f"RED {pn}",ground,fc,True)
    if post(f"🟥 RED CARD! {mt} {pn}\n\n{lg}\n{hn} {hs}-{as_} {an}\n\nGame changer? 👇 🔔 FOLLOW!\n\n{tag}",img):
     st.setdefault("red",{})[rid]=1; posted+=1
  for pn,mt,fc,it in pml:
   rid=f"{eid}_pmiss_{pn}_{mt}"
   if rid not in st.get("pen_miss",{}):
    if not fc: fc=scorer_face(pn)
    img=mk_img(hn,an,f"{hs}-{as_}",lg,f"MISSED PEN {mt}",f"MISSED PEN {pn}",ground,fc,False,True)
    if post(f"❌ MISSED PENALTY! {mt} {pn}\n\n{lg}\n{hn} {hs}-{as_} {an}\n\nShould he score? 👇\n\n{tag}",img):
     st.setdefault("pen_miss",{})[rid]=1; posted+=1
  for pn,mt,fc,it in pgl:
   rid=f"{eid}_pgoal_{pn}_{mt}"
   if rid not in st.get("pen_goal",{}):
    if not fc: fc=scorer_face(pn)
    img=mk_img(hn,an,f"{hs}-{as_}",lg,f"PENALTY {mt}",f"PENALTY {pn}",ground,fc)
    if post(f"⚽ PENALTY GOAL! {mt} {pn}\n\n{lg}\n{hn} {hs}-{as_} {an}\n\n{tag}",img):
     st.setdefault("pen_goal",{})[rid]=1; posted+=1
  for pn,mt,fc,it in varl:
   rid=f"{eid}_var_{pn}_{mt}"
   if rid not in st.get("var",{}):
    if not fc and pn: fc=scorer_face(pn)
    img=mk_img(hn,an,f"{hs}-{as_}",lg,f"VAR {mt}",f"VAR CHECK {pn}",ground,fc,False,True)
    if post(f"📺 VAR CHECK! {mt} {pn}\n\n{lg}\n{hn} {hs}-{as_} {an}\n\nGoal or no? Comment 👇\n\n{tag}",img):
     st.setdefault("var",{})[rid]=1; posted+=1
  if status=="STATUS_HALFTIME" and eid not in st.get("ht",{}):
   img=mk_img(hn,an,f"{hs}-{as_}",lg,"HT","HALFTIME",ground)
   if post(f"⏸️ HALFTIME\n\n{lg}\n{hn} {hs}-{as_} {an}\n\n2nd half prediction? 👇 🔔 FOLLOW!\n\n{tag}",img):
    st.setdefault("ht",{})[eid]=1; posted+=1
  if status=="STATUS_FINAL" and eid not in st.get("ft",{}):
   img=mk_img(hn,an,f"{hs}-{as_}",lg,"FT","FULL TIME",ground)
   if post(f"✅ FULL TIME\n\n{lg}\n{hn} {hs}-{as_} {an}\n\nRate game 1-10 👇 FOLLOW for all results! 🌍\n\n{tag}",img):
    st.setdefault("ft",{})[eid]=1; posted+=1
 return posted

def main():
 st=load(); tot=0
 for i in range(6):
  tot+=run_once(st); save(st)
  if i<5: time.sleep(10)
 now=datetime.now().timestamp()
 if (now - st.get("last_news_time",0))>720:
  news=fetch_news(); random.shuffle(news)
  for n in news[:20]:
   ttl=n["title"][:80]
   if ttl.lower() in [x.lower() for x in st.get("news",[])]:
    continue
   if len(ttl)<15: continue
   real=n.get("hd")
   if not real:
    url=n.get("img_url")
    if url: real=dl(url)
   if not real: continue
   if real.size[0]<400: continue
   img=mk_news_img(real)
   src=n.get("source") or src_name(n["link"])
   low=(n["title"]+" "+n["desc"]).lower()
   is_kpl="kenya" in low or "kpl" in low or "gor" in low
   is_uk=any(x in low for x in ["arsenal","man utd","liverpool","chelsea","premier league"])
   is_usa="mls" in low or "messi" in low or "inter miami" in low
   if is_kpl: hashtags="#KPL #KenyaFootball #AfricanFootball #ViralKE #FootballKE"
   elif is_uk: hashtags="#PremierLeague #UKFootball #Arsenal #ManUtd #ViralUK #FootballUK"
   elif is_usa: hashtags="#MLS #Messi #USASoccer #ViralUSA #FootballUSA"
   else: hashtags="#FootballNews #WorldFootball #ViralFootball"
   cap=f"🟢 {n['title']}\n\n{n['desc']}\n\nSource: {src}\n\nYour thoughts? Comment 👇 Share! 🔔 FOLLOW NOW - Fastest in UK Africa USA! 🌍\n\n{hashtags}"
   if post(cap,img):
    st.setdefault("news",[]).append(ttl); st["last_news_time"]=now; tot+=1; break
 print(f"V51 FIXED DONE {tot}"); save(st)

if __name__=="__main__":
 main()
