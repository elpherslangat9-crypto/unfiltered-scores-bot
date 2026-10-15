# V71 V69 CO-OPERATE - FIX FB 400 SPAM - 1 POST PER RUN - NO PHOTO LIVE - ALL FEATURES V69
print("V71 V69 COOPERATE LOADED")
import os,json,requests,re,random,time,xml.etree.ElementTree as ET
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image,ImageDraw,ImageFont
from concurrent.futures import ThreadPoolExecutor

PID=os.getenv("PAGE_ID")
TOK=os.getenv("PAGE_ACCESS_TOKEN") or os.getenv("FB_TOKEN")
FILE="posted_state.json"
NAMES={"eng.1":"Premier League","esp.1":"LaLiga","ger.1":"Bundesliga","ita.1":"Serie A","fra.1":"Ligue 1","ken.1":"KPL","usa.1":"MLS","uefa.champions":"UCL","uefa.europa":"Europa","eng.2":"Championship"}
PR=list(NAMES.keys())
BIG=["Premier League","KPL","UCL"]
BAD=["rugby","cricket","tennis","golf","boxing","nfl","nba"]
BADP=["lens","sporting cp","slavia praha","goal scorer","unknown","home team","away team"]

def load():
 d={"last":{},"goals":{},"ht":{},"ft":{},"red":{},"pen":{},"kick":{},"lineup":{},"news":[],"last_news_time":0}
 try: return {**d,**json.load(open(FILE))}
 except: return d
def save(s): open(FILE,"w").write(json.dumps(s))

def mk_text(h,a,sc,lg,top,bottom,red=False,pen=False):
 W,H=1080,1080
 bg=(70,12,12) if red else (12,12,70) if pen else (15,25,15)
 img=Image.new("RGB",(W,H),bg);d=ImageDraw.Draw(img)
 try: fb=ImageFont.truetype("DejaVuSans-Bold.ttf",90);fm=ImageFont.truetype("DejaVuSans-Bold.ttf",48);fs=ImageFont.truetype("DejaVuSans-Bold.ttf",32)
 except: fb=fm=fs=ImageFont.load_default()
 col=(0,255,100) if not red and not pen else (255,40,40) if red else (255,220,0)
 d.rounded_rectangle([30,20,1050,85],radius=18,fill=col);d.text((45,28),f"{lg} {top}"[:36],font=fs,fill=(0,0,0))
 d.text((60,180),h.upper()[:22],font=fm,fill=(255,255,255));d.text((60,250),a.upper()[:22],font=fm,fill=(255,255,255))
 d.rounded_rectangle([320,420,760,550],radius=28,fill=(255,255,255));d.text((370,440),sc,font=fb,fill=(0,0,0))
 d.rounded_rectangle([30,1000,1050,1050],radius=18,fill=col);d.text((40,1008),bottom[:48],font=fs,fill=(0,0,0))
 p="/tmp/m.jpg";img.save(p,"JPEG",quality=92);return p

def post(msg,path):
 # FIXED POST - PRINTS REAL ERROR + 1 BY 1
 try:
  with open(path,"rb") as f:
   r=requests.post(f"https://graph.facebook.com/v20.0/{PID}/photos",data={"caption":msg,"access_token":TOK},files={"source":f},timeout=30)
  print(f"FB {r.status_code} {r.text[:400]}")
  if r.status_code==200:
   time.sleep(3) # COOPERATE WITH FB - DELAY
   return True
  # If photos blocked, try feed text
  if r.status_code==400:
   r2=requests.post(f"https://graph.facebook.com/v20.0/{PID}/feed",data={"message":msg,"access_token":TOK},timeout=15)
   print(f"FALLBACK FEED {r2.status_code} {r2.text[:400]}")
   if r2.status_code==200:
    time.sleep(3);return True
  return False
 except Exception as e:
  print(f"POST ERR {e}");return False

def dl(u):
 try:
  from io import BytesIO
  r=requests.get(u,timeout=7);
  from PIL import Image as Im
  return Im.open(BytesIO(r.content)).convert("RGB") if len(r.content)>3000 else None
 except: return None

def get_sb(lg):
 try:
  j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/scoreboard",timeout=6).json()
  return [{**e,"_code":lg,"_lname":NAMES.get(lg,lg)} for e in j.get("events",[])]
 except: return []

def get_sum(ar):
 eid,code=ar
 try:
  j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/summary?event={eid}",timeout=6).json()
  return {"d":j.get("header",{}).get("competitions",[{}])[0].get("details",[]) or [],"l":j.get("lineups") or []}
 except: return {"d":[],"l":[]}

def get_fast_inc(h,a):
 g=[];r=[];p=[]
 try:
  j=requests.get(f"https://api.sofascore.app/api/v1/search/all?q={h} {a}",timeout=5,headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.sofascore.com/"}).json()
  for res in j.get("results",[])[:2]:
   if res.get("type")=="event":
    sid=res.get("entity",{}).get("id")
    if not sid: continue
    inc=requests.get(f"https://api.sofascore.app/api/v1/event/{sid}/incidents",timeout=5,headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.sofascore.com/"}).json()
    for it in inc.get("incidents",[])[:30]:
     pn=it.get("player",{}).get("name","");tm=it.get("time",0)
     if not pn or len(pn)<3 or pn.lower() in BADP or pn.lower() in [h.lower(),a.lower()]: continue
     if it.get("incidentType")=="goal": g.append((pn,f"{tm}'"))
     if it.get("incidentType")=="card" and it.get("incidentClass")=="red": r.append((pn,f"{tm}'"))
     if "penalty" in str(it).lower(): p.append((pn,f"{tm}'"))
    break
 except: pass
 return g,r,p

def run_once(st):
 all_ev=[]
 with ThreadPoolExecutor(max_workers=10) as ex:
  for lst in ex.map(get_sb,PR): all_ev.extend(lst)
 print(f"LIVE {len(all_ev)}")
 sums={}
 ids=[(e["id"],e["_code"]) for e in all_ev]
 with ThreadPoolExecutor(max_workers=12) as ex:
  for e,s in zip(all_ev, ex.map(get_sum, ids)): sums[e["id"]]=s

 for ev in all_ev: # ONE POST ONLY PER RUN TO COOPERATE
  eid=ev["id"];comp=ev["competitions"][0];status=comp["status"]["type"]["name"];short=comp["status"]["type"].get("shortDetail","")
  try: h=next(x for x in comp["competitors"] if x["homeAway"]=="home");a=next(x for x in comp["competitors"] if x["homeAway"]=="away")
  except: continue
  hn,an=h["team"]["displayName"],a["team"]["displayName"];hs,as_=str(h.get("score","0")),str(a.get("score","0"));lg=ev["_lname"]
  is_big=lg in BIG
  FOLLOW="#UnfilteredScores #FollowForLive #FOLLOW #LiveScores #FootballKE #Viral"
  m=re.search(r"(\d+)'",short);minute=int(m.group(1)) if m else 0
  last=st.get("last",{}).get(eid,"0-0")

  # KICKOFF
  if status in ["STATUS_IN_PROGRESS","STATUS_HALFTIME"] and eid not in st["kick"]:
   img=mk_text(hn,an,"0-0",lg,"KICK OFF","KICK OFF")
   if post(f"KICK OFF! {hn} vs {an}\n{lg}\n{FOLLOW}",img):
    st["kick"][eid]=1;st["last"][eid]=f"{hs}-{as_}";return 1

  # GOAL - DIRECT NO LENS BUG
  if status in ["STATUS_IN_PROGRESS","STATUS_HALFTIME"] and last!=f"{hs}-{as_}":
   if not (last=="0-0" and hs=="0" and as_=="0"):
    gid=eid+"_"+f"{hs}-{as_}"
    if gid not in st["goals"]:
     gl,rl,pl=get_fast_inc(hn,an)
     pname="";mt=f"{minute}'" if minute else "LIVE"
     for d in sums.get(eid,{}).get("d",[])[-5:]:
      if "goal" in str(d.get("type","")).lower():
       cand=d.get("athlete",{}).get("displayName","")
       if cand and cand.lower() not in BADP: pname=cand;break
     if not pname and gl:
      for pn,mt2 in reversed(gl):
       if pn.lower() not in BADP: pname=pn;mt=mt2;break
     if pname and pname.lower() not in BADP:
      img=mk_text(hn,an,f"{hs}-{as_}",lg,f"{mt} GOAL",f"{pname} {mt}")
      if post(f"{hn} {hs}-{as_} {an} | {mt} {pname}\n{lg}\n{FOLLOW}",img):
       st["goals"][gid]=1;st["last"][eid]=f"{hs}-{as_}";return 1

  st["last"][eid]=f"{hs}-{as_}"

  # RED
  _,rl,_=get_fast_inc(hn,an)
  for pn,mt in rl[:1]:
   if pn.lower() in BADP: continue
   rid=eid+"_red_"+pn+"_"+mt
   if rid not in st["red"]:
    img=mk_text(hn,an,f"{hs}-{as_}",lg,f"RED {mt}",f"{pn} RED",red=True)
    if post(f"{hn} {hs}-{as_} {an} | RED {mt} {pn}\n{lg}\n{FOLLOW}",img):
     st["red"][rid]=1;return 1

  # HT/FT BIG ONLY
  if is_big and status=="STATUS_HALFTIME" and eid not in st["ht"]:
   img=mk_text(hn,an,f"{hs}-{as_}",lg,"HT","HALFTIME")
   if post(f"{hn} {hs}-{as_} {an} | HALFTIME\n{lg}\n{FOLLOW}",img): st["ht"][eid]=1;return 1
  if is_big and status=="STATUS_FINAL" and eid not in st["ft"]:
   img=mk_text(hn,an,f"{hs}-{as_}",lg,"FT","FULL TIME")
   if post(f"{hn} {hs}-{as_} {an} | FULL TIME\n{lg}\n{FOLLOW}",img): st["ft"][eid]=1;return 1
 return 0

def main():
 st=load()
 for i in range(3): # ONLY 3 LOOPS, 1 POST PER LOOP = FB HAPPY
  print(f"LOOP {i+1}")
  if run_once(st)==1:
   save(st);print("POSTED 1 - STOP TO COOPERATE");break
  save(st);time.sleep(2)
 print("V71 DONE");save(st)
if __name__=="__main__": main()
