# V42 FINAL - 8 LEAGUES + NEWS - ALL FEATURES
import os,json,requests,re,random,time
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
 "eng.1":"Premier League","esp.1":"LaLiga","fra.1":"Ligue 1",
 "ita.1":"Serie A","ger.1":"Bundesliga","ken.1":"KPL",
 "uefa.champions":"Champions League","uefa.europa":"Europa League"
}
PR=["eng.1","esp.1","fra.1","ita.1","ger.1","ken.1","uefa.champions","uefa.europa"]
BIG={"real madrid":(255,255,255),"barcelona":(20,20,120),"man city":(108,171,223),"arsenal":(239,1,7)}

def load():
 d={"lineup":{},"goals":{},"ht":{},"ft":{},"last":{},"red":{},"kick":{},"news":[],"last_news_time":0}
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
  r=requests.get(u,timeout=8,headers={"User-Agent":"Mozilla/5.0"})
  if r.status_code==200 and len(r.content)>4000:
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

def real_photo(eid,code,home,away):
 try:
  j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/summary?event={eid}",timeout=4).json()
  pics=j.get("header",{}).get("pics") or []
  for p in pics:
   href=p.get("href")
   if href:
    im=dl(href)
    if im: return im
 except: pass
 try:
  j=requests.get(f"https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t={home}",timeout=4).json()
  tm=j.get("teams",[]) or []
  if tm and tm[0].get("strStadiumThumb"):
   im=dl(tm[0]["strStadiumThumb"])
   if im: return im
 except: pass
 return None

def fast_inc(home,away):
 g=[]; r=[]
 try:
  j=requests.get(f"https://api.sofascore.app/api/v1/search/all?q={home} {away}",timeout=4,headers={"User-Agent":"Mozilla/5.0"}).json()
  for res in j.get("results",[])[:3]:
   if res.get("type")=="event":
    sid=res.get("entity",{}).get("id")
    if not sid: continue
    inc=requests.get(f"https://api.sofascore.app/api/v1/event/{sid}/incidents",timeout=4,headers={"User-Agent":"Mozilla/5.0"}).json()
    for it in inc.get("incidents",[]):
     tp=it.get("incidentType",""); pn=it.get("player",{}).get("name",""); mn=it.get("time",0); pid=it.get("player",{}).get("id")
     ph=None
     if pid: ph=dl(f"https://api.sofascore.app/api/v1/player/{pid}/image")
     if tp=="goal": g.append((pn,f"{mn}'",ph,it))
     if tp=="card" and it.get("incidentClass")=="red": r.append((pn,f"{mn}'",ph))
    if g or r: break
 except: pass
 return g,r

def src_name(link):
 try:
  d=urlparse(link).netloc.lower()
  if "skysports" in d: return "Sky Sports"
  if "bbc" in d: return "BBC Sport"
  if "espn" in d: return "ESPN"
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

def mk_img(h,a,sc,lg,top,bot,ground,face=None,red=False):
 W,H=1080,1350
 bg=bg_real(h,ground)
 if red: bg=Image.new("RGB",(W,H),(50,10,10))
 d=ImageDraw.Draw(bg)
 try: fb=ImageFont.truetype("DejaVuSans-Bold.ttf",90); fs=ImageFont.truetype("DejaVuSans-Bold.ttf",34)
 except: fb=fs=ImageFont.load_default()
 col=(0,255,100) if not red else (255,0,0)
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
  real=real.convert("RGB"); rw,rh=real.size; ra=max(W/rw,H/rh)
  ns=(int(rw*ra),int(rh*ra)); bg=real.resize(ns,Image.LANCZOS); l=(ns[0]-W)//2; t=(ns[1]-H)//2; bg=bg.crop((l,t,l+W,t+H))
 except: bg=real.resize((W,H),Image.LANCZOS)
 d=ImageDraw.Draw(bg,"RGBA")
 try: fs=ImageFont.truetype("DejaVuSans-Bold.ttf",36)
 except: fs=ImageFont.load_default()
 d.rounded_rectangle([15,15,W-15,80],radius=20,fill=(0,255,100)); d.text((35,28),"Unfiltered Scores - BREAKING",font=fs,fill=(0,0,0))
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
  det=j.get("header",{}).get("competitions",[{}])[0].get("details",[]) or []
  lin=j.get("lineups") or []
  return {"d":det,"l":lin}
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
 news=[]
 try:
  j=requests.get("https://site.api.espn.com/apis/site/v2/sports/soccer/news",timeout=6).json()
  for a in j.get("articles",[])[:10]:
   ttl=a.get("headline",""); lnk=a.get("links",{}).get("web",{}).get("href",""); ims=a.get("images",[]); img=ims[0].get("url") if ims else None
   if ttl and img: news.append({"title":ttl,"link":lnk,"img":img,"desc":a.get("description","")[:200]})
 except: pass
 return news

def run_once(st):
 all_ev=[]
 with ThreadPoolExecutor(max_workers=8) as ex:
  for lst in ex.map(get_sb,PR): all_ev.extend(lst)
 live=[e for e in all_ev if e["competitions"][0]["status"]["type"]["name"] in ["STATUS_IN_PROGRESS","STATUS_HALFTIME","STATUS_SCHEDULED","STATUS_FINAL"]]
 sums={}
 with ThreadPoolExecutor(max_workers=12) as ex:
  ids=[(e["id"],e["_code"]) for e in live]
  for e,s in zip(live,ex.map(get_sum,ids)): sums[e["id"]]=s
 posted=0
 for ev in live:
  eid=ev["id"]; code=ev["_code"]; comp=ev["competitions"][0]; status=comp["status"]["type"]["name"]; short=comp["status"]["type"].get("shortDetail","")
  comps=comp["competitors"]
  try: h=next(x for x in comps if x["homeAway"]=="home"); a=next(x for x in comps if x["homeAway"]=="away")
  except: continue
  hn,an=h["team"]["displayName"],a["team"]["displayName"]; hs,as_=str(h.get("score","0")),str(a.get("score","0")); lg=ev["_lname"]
  summ=sums.get(eid,{"d":[],"l":[]}); details=summ["d"]; lins=summ["l"]
  m=re.search(r"(\d+)'",short); minute=int(m.group(1)) if m else 0
  ground=real_photo(eid,code,hn,an)
  try:
   ds=comp.get("date",""); dt=datetime.fromisoformat(ds.replace("Z","+00:00")).astimezone(EAT)
   df=dt.strftime("%a %d %b %Y"); tf=dt.strftime("%I:%M %p"); hrs=(dt - datetime.now(EAT)).total_seconds()/3600
  except: df=tf=""; hrs=999
  if status=="STATUS_SCHEDULED" and eid not in st.get("lineup",{}):
   if hrs<=2.5 and hrs>=-0.5:
    txt=lineup_txt(lins)
    if txt and len(txt)>30:
     bg=bg_real(hn,ground)
     d=ImageDraw.Draw(bg)
     try: fs=ImageFont.truetype("DejaVuSans-Bold.ttf",32)
     except: fs=ImageFont.load_default()
     d.rounded_rectangle([30,20,1050,85],radius=20,fill=(0,255,100)); d.text((50,30),f"LINEUP {lg}",font=fs,fill=(0,0,0))
     p="/tmp/m.png"; bg.save(p,quality=90)
     if post(f"LINEUP {lg}\n\n{hn} vs {an}\n\n{df} {tf} EAT\n\n{txt}Unfiltered Scores",p):
      st.setdefault("lineup",{})[eid]=1; posted+=1
  if status=="STATUS_IN_PROGRESS" and eid not in st.get("kick",{}):
   if minute<=3:
    img=mk_img(hn,an,"0-0",lg,"KICK OFF",f"KICK OFF {hn} vs {an}",ground)
    if post(f"KICK OFF! {lg}\n\n{hn} vs {an} kicked off!\n\n{df} {tf} EAT\n\nUnfiltered Scores LIVE",img):
     st.setdefault("kick",{})[eid]=1; posted+=1
  gl,rl=fast_inc(hn,an)
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
      if pn: pname=pn
      face=fc
      if it and "penalty" in str(it).lower(): is_pen=True
     if not face and pname: face=scorer_face(pname,pid)
     if not pname: pname=hn
     label="PENALTY" if is_pen else f"{mt} GOAL"
     img=mk_img(hn,an,f"{hs}-{as_}",lg,label,f"{label} {pname}",ground,face)
     if post(f"GOAL! {label}! {mt} {pname}\n\n{lg}\n{hn} {hs}-{as_} {an}\n\nUnfiltered Scores LIVE",img):
      st.setdefault("goals",{})[gid]=1; posted+=1
  st.setdefault("last",{})[eid]=f"{hs}-{as_}"
  for pn,mt,fc in rl:
   rid=f"{eid}_red_{pn}_{mt}"
   if rid not in st.get("red",{}):
    if not fc: fc=scorer_face(pn)
    img=mk_img(hn,an,f"{hs}-{as_}",lg,f"RED {mt}",f"RED {pn}",ground,fc,True)
    if post(f"RED CARD! {mt}\n\n{lg}\n{hn} {hs}-{as_} {an}\n\n{pn} sent off!",img):
     st.setdefault("red",{})[rid]=1; posted+=1
  if status=="STATUS_HALFTIME" and eid not in st.get("ht",{}):
   img=mk_img(hn,an,f"{hs}-{as_}",lg,"HT","HALFTIME",ground)
   if post(f"HALFTIME\n\n{lg}\n{hn} {hs}-{as_} {an}",img):
    st.setdefault("ht",{})[eid]=1; posted+=1
  if status=="STATUS_FINAL" and eid not in st.get("ft",{}):
   img=mk_img(hn,an,f"{hs}-{as_}",lg,"FT","FULL TIME",ground)
   if post(f"FULL TIME\n\n{lg}\n{hn} {hs}-{as_} {an}",img):
    st.setdefault("ft",{})[eid]=1; posted+=1
 return posted

def main():
 st=load(); tot=0
 for i in range(6):
  tot+=run_once(st); save(st)
  if i<5: time.sleep(10)
 # NEWS - AS DISCUSSED - CLEAR HD + SOURCE ONLY + 20 MIN GAP
 now=datetime.now().timestamp()
 if (now - st.get("last_news_time",0))>1200:
  news=fetch_news(); random.shuffle(news)
  for n in news[:10]:
   ttl=n["title"][:80]
   if ttl.lower() in [x.lower() for x in st.get("news",[])]:
    continue
   real=dl(n["img"])
   if not real: continue
   img=mk_news_img(real)
   src=src_name(n["link"])
   cap=f"{n['title']}\n\n{n['desc']}\n\nSource: {src}\n\nUnfiltered Scores\n#UnfilteredScores"
   if post(cap,img):
    st.setdefault("news",[]).append(ttl); st["last_news_time"]=now; tot+=1; break
 print(f"V42 DONE {tot}"); save(st)

if __name__=="__main__":
 main()
