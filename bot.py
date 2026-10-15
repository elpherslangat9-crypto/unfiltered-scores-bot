# V69 FINAL BALANCED VIRAL - NO PHOTO LIVE - KICKOFF GOAL RED PENALTY HT FT BIG GAMES ONLY - LINEUP BIG ONLY - NEWS PHOTO FOOTBALL ONLY
print("V69 BALANCED VIRAL LOADED")
import os,json,requests,re,random,time,xml.etree.ElementTree as ET
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image,ImageDraw,ImageFont
from concurrent.futures import ThreadPoolExecutor

PID=os.getenv("PAGE_ID");TOK=os.getenv("PAGE_ACCESS_TOKEN") or os.getenv("FB_TOKEN")
FILE="posted_state.json";EAT=ZoneInfo("Africa/Nairobi")

# ALL LEAGUES FOR FAST CATCH, BUT HT/FT ONLY BIG 3
NAMES={"eng.1":"Premier League","esp.1":"LaLiga","ger.1":"Bundesliga","ita.1":"Serie A","fra.1":"Ligue 1","ken.1":"KPL","usa.1":"MLS","uefa.champions":"UCL","uefa.europa":"Europa","eng.2":"Championship"}
PR=list(NAMES.keys())
BIG_GAMES=["Premier League","KPL","UCL"] # HT/FT/Lineup only these = no spam
BAD_NEWS=["rugby","cricket","tennis","golf","boxing","nfl","nba","baseball","hockey","athletics","f1"]
BADP=["lens","rc lens","sporting cp","slavia praha","slavia prage","sporting","goal scorer","unknown","own goal","home team","away team"]

def load():
 d={"lineup":{},"goals":{},"ht":{},"ft":{},"last":{},"red":{},"pen":{},"kick":{},"news":[],"last_news_time":0}
 try: return {**d,**json.load(open(FILE))}
 except: return d
def save(s): open(FILE,"w").write(json.dumps(s))

def mk_text(h,a,sc,lg,top,bottom,red=False,pen=False):
 W,H=1080,1080
 if red: bg=(70,12,12)
 elif pen: bg=(12,12,70)
 else: bg=(10,22,12)
 img=Image.new("RGB",(W,H),bg);d=ImageDraw.Draw(img)
 try: fb=ImageFont.truetype("DejaVuSans-Bold.ttf",95);fm=ImageFont.truetype("DejaVuSans-Bold.ttf",50);fs=ImageFont.truetype("DejaVuSans-Bold.ttf",33)
 except: fb=fm=fs=ImageFont.load_default()
 col=(0,255,100) if not red and not pen else (255,40,40) if red else (255,220,0)
 d.rounded_rectangle([30,20,1050,85],radius=20,fill=col);d.text((50,30),f"{lg} {top}"[:38],font=fs,fill=(0,0,0))
 d.text((60,180),h.upper()[:20],font=fm,fill=(255,255,255));d.text((60,260),a.upper()[:20],font=fm,fill=(255,255,255))
 d.rounded_rectangle([300,450,780,580],radius=30,fill=(255,255,255));d.text((360,470),sc,font=fb,fill=(0,0,0))
 d.rounded_rectangle([30,1000,1050,1060],radius=20,fill=col);d.text((40,1010),bottom[:52],font=fs,fill=(0,0,0))
 p="/tmp/m.png";img.save(p);return p

def post(msg,path):
 try:
  r=requests.post(f"https://graph.facebook.com/v20.0/{PID}/photos",data={"caption":msg,"access_token":TOK},files={"source":open(path,"rb")},timeout=20)
  print(f"FB {r.status_code}");return r.status_code==200
 except: return False

def dl(u):
 try:
  from io import BytesIO
  from PIL import Image as Im
  r=requests.get(u,timeout=7,headers={"User-Agent":"Mozilla/5.0"})
  return Im.open(BytesIO(r.content)).convert("RGBA") if len(r.content)>3000 else None
 except: return None

def get_sb(lg):
 try:
  j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/scoreboard",timeout=5).json()
  return [{**e,"_code":lg,"_lname":NAMES.get(lg,lg)} for e in j.get("events",[])]
 except: return []

def get_sum(ar):
 eid,code=ar
 try:
  j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/summary?event={eid}",timeout=5).json()
  return {"d":j.get("header",{}).get("competitions",[{}])[0].get("details",[]) or [],"l":j.get("lineups") or []}
 except: return {"d":[],"l":[]}

def get_fast():
 ev=[];H={"User-Agent":"Mozilla/5.0","Referer":"https://www.sofascore.com/"}
 try:
  r=requests.get("https://api.sofascore.app/api/v1/sport/football/events/live",timeout=7,headers=H)
  for e in r.json().get("events",[]):
   try:
    name=(e.get("homeTeam",{}).get("name","")+e.get("awayTeam",{}).get("name","")).lower()
    tour=(e.get("tournament",{}).get("name","")+e.get("tournament",{}).get("category",{}).get("name","")).lower()
    code="ken.1" if "kenya" in tour or "gor" in name or "leopards" in name else "eng.1" if "premier" in tour else "uefa.champions" if "champions" in tour else "esp.1" if "la liga" in tour else None
    if not code: continue
    hs=str(e.get("homeScore",{}).get("current",0));ass=str(e.get("awayScore",{}).get("current",0))
    st=e.get("status",{}).get("type","");mp={"inprogress":"STATUS_IN_PROGRESS","halftime":"STATUS_HALFTIME","finished":"STATUS_FINAL"};stype=mp.get(st,"STATUS_SCHEDULED");mn=e.get("time",{}).get("minute",0)
    ev.append({"id":"sofa_"+str(e.get('id')),"_code":code,"_lname":NAMES.get(code,code),"competitions":[{"status":{"type":{"name":stype,"shortDetail":f"{mn}'"}},"competitors":[{"homeAway":"home","team":{"displayName":e.get("homeTeam",{}).get("name","")},"score":hs},{"homeAway":"away","team":{"displayName":e.get("awayTeam",{}).get("name","")},"score":ass}],"date":""}]})
   except:0
 except:0
 return ev

def fast_inc(h,a):
 g=[];r=[];p=[]
 try:
  j=requests.get(f"https://api.sofascore.app/api/v1/search/all?q={h} {a}",timeout=4,headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.sofascore.com/"}).json()
  for res in j.get("results",[])[:2]:
   if res.get("type")=="event":
    sid=res.get("entity",{}).get("id")
    if not sid: continue
    inc=requests.get(f"https://api.sofascore.app/api/v1/event/{sid}/incidents",timeout=4,headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.sofascore.com/"}).json()
    for it in inc.get("incidents",[])[:35]:
     pn=it.get("player",{}).get("name","");mn=it.get("time",0)
     if not pn or len(pn)<3 or pn.lower() in BADP or pn.lower() in [h.lower(),a.lower()]: continue
     if it.get("incidentType")=="goal": g.append((pn,f"{mn}'"))
     if it.get("incidentType")=="card" and it.get("incidentClass")=="red": r.append((pn,f"{mn}'"))
     if "penalty" in str(it.get("incidentType","")).lower() or "penalty" in str(it.get("text","")).lower(): p.append((pn,f"{mn}'"))
    if g or r or p: break
 except:0
 return g,r,p

def get_hd(u):
 try:
  r=requests.get(u,timeout=6);m=re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',r.text,re.I)
  if m:
   uu=m.group(1);uu="https:"+uu if uu.startswith("//") else uu
   im=dl(uu)
   if im and im.size[0]>300: return im
 except:0
 return None

def fetch_news():
 news=[]
 try:
  j=requests.get("https://site.api.espn.com/apis/site/v2/sports/soccer/news",timeout=7).json()
  for a in j.get("articles",[])[:15]:
   ttl=a.get("headline","");img=a.get("images",[{}])[0].get("url") if a.get("images") else None
   if ttl and img and not any(b in ttl.lower() for b in BAD_NEWS):
    im=dl(img)
    if im: news.append({"title":ttl,"desc":a.get("description","")[:180],"source":"ESPN","hd":im})
 except:0
 for url in ["https://www.skysports.com/rss/12040","http://feeds.bbci.co.uk/sport/football/rss.xml"]:
  try:
   r=requests.get(url,timeout=7);root=ET.fromstring(r.content)
   for item in root.findall(".//item")[:12]:
    ttl=item.findtext("title","")
    if ttl and not any(b in ttl.lower() for b in BAD_NEWS):
     hd=get_hd(item.findtext("link",""))
     if hd: news.append({"title":ttl,"desc":item.findtext("description","")[:180],"source":"Sky/BBC","hd":hd})
  except:0
 return news

def mk_news(real):
 W,H=1080,1350
 try: rw,rh=real.size;ratio=min(W/rw,(H-80)/rh);nw=int(rw*ratio);nh=int(rh*ratio);fg=real.resize((nw,nh),Image.LANCZOS);bg=Image.new("RGB",(W,H),(0,0,0));bg.paste(fg,((W-nw)//2,80+(H-80-nh)//2))
 except: bg=Image.new("RGB",(W,H),(0,0,0))
 d=ImageDraw.Draw(bg);d.rounded_rectangle([15,15,280,65],radius=20,fill=(0,255,100))
 try: fs=ImageFont.truetype("DejaVuSans-Bold.ttf",32)
 except: fs=ImageFont.load_default()
 d.text((30,26),"Unfiltered Scores",font=fs,fill=(0,0,0))
 p="/tmp/news.png";bg.save(p,quality=100);return p

def run_once(st):
 all_ev=[]
 with ThreadPoolExecutor(max_workers=12) as ex:
  for lst in ex.map(get_sb,PR): all_ev.extend(lst)
 all_ev.extend(get_fast())
 live=[e for e in all_ev if e["competitions"][0]["status"]["type"]["name"] in ["STATUS_IN_PROGRESS","STATUS_HALFTIME","STATUS_SCHEDULED","STATUS_FINAL"]]
 print(f"LIVE {len(live)}")
 sums={}
 with ThreadPoolExecutor(max_workers=15) as ex:
  ids=[(e["id"],e["_code"]) for e in live if not str(e["id"]).startswith("sofa_")];evs=[e for e in live if not str(e["id"]).startswith("sofa_")]
  for e,s in zip(evs, ex.map(get_sum, ids)): sums[e["id"]]=s
 posted=0
 for ev in live:
  eid=ev["id"];comp=ev["competitions"][0];status=comp["status"]["type"]["name"];short=comp["status"]["type"].get("shortDetail","")
  try: h=next(x for x in comp["competitors"] if x["homeAway"]=="home");a=next(x for x in comp["competitors"] if x["homeAway"]=="away")
  except: continue
  hn,an=h["team"]["displayName"],a["team"]["displayName"];hs,as_=str(h.get("score","0")),str(a.get("score","0"));lg=ev["_lname"]
  is_big=lg in BIG_GAMES
  FOLLOW=f"#UnfilteredScores #FollowForLive #FOLLOW #LiveScores #{lg.replace(' ','')} #FootballKE #Viral #FYP"
  m=re.search(r"(\d+)'",short);minute=int(m.group(1)) if m else 0
  last=st.get("last",{}).get(eid,"0-0")

  # KICKOFF - ALL LEAGUES
  if status in ["STATUS_IN_PROGRESS","STATUS_HALFTIME"] and eid not in st["kick"]:
   img=mk_text(hn,an,"0-0",lg,"KICK OFF","KICK OFF")
   if post(f"KICK OFF! {hn} vs {an}\n{lg}\nFollow Unfiltered Scores for LIVE goals!\n{FOLLOW}",img): st["kick"][eid]=1;posted+=1

  # LINEUP - BIG GAMES ONLY
  if is_big and status=="STATUS_SCHEDULED" and eid not in st["lineup"]:
   lineups=sums.get(eid,{}).get("l",[]) if not str(eid).startswith("sofa_") else []
   if lineups and len(lineups)>=2:
    txt=""
    for lu in lineups[:2]:
     tn=lu.get("team",{}).get("displayName","Team");txt+=tn+":\n"
     for ath in lu.get("athletes",[])[:11]: txt+=ath.get("athlete",{}).get("displayName","")+", "
     txt+="\n\n"
    if len(txt)>60:
     img=mk_text(hn,an,"VS",lg,"LINEUP",f"{lg} LINEUP")
     if post(f"LINEUP! {hn} vs {an}\n{lg}\n{txt[:450]}\nWho wins? 👇\n{FOLLOW}",img): st["lineup"][eid]=1;posted+=1

  gl,rl,pl=fast_inc(hn,an)

  # GOAL - ALL LEAGUES DIRECT
  if status in ["STATUS_IN_PROGRESS","STATUS_HALFTIME"] and last!=f"{hs}-{as_}":
   if not (last=="0-0" and hs=="0" and as_=="0"):
    gid=eid+"_"+f"{hs}-{as_}"
    if gid not in st["goals"]:
     pname="";mt=f"{minute}'" if minute>0 else "LIVE"
     for d in sums.get(eid,{}).get("d",[])[-6:]:
      if "goal" in str(d.get("type","")).lower():
       cand=d.get("athlete",{}).get("displayName","")
       if cand and cand.lower() not in BADP and cand.lower() not in [hn.lower(),an.lower()]: pname=cand;mt=d.get("clock",{}).get("displayValue","") or mt;break
     if gl:
      for pn,mt2 in reversed(gl):
       if pn.lower() not in BADP and pn.lower() not in [hn.lower(),an.lower()]: pname=pn;mt=mt2;break
     if pname and pname.lower() not in BADP:
      img=mk_text(hn,an,f"{hs}-{as_}",lg,f"{mt} GOAL",f"{pname} {mt}")
      if post(f"{hn} {hs}-{as_} {an} | {mt} {pname} SCORES!\n{lg}\nFollow for live updates! 👇\n{FOLLOW}",img): st["goals"][gid]=1;posted+=1
  st["last"][eid]=f"{hs}-{as_}"

  # RED CARD - ALL LEAGUES
  for pn,mt in rl:
   if pn.lower() in BADP or pn.lower() in [hn.lower(),an.lower()]: continue
   rid=eid+"_red_"+pn+"_"+mt
   if rid not in st["red"]:
    img=mk_text(hn,an,f"{hs}-{as_}",lg,f"RED {mt}",f"{pn} RED",red=True)
    if post(f"{hn} {hs}-{as_} {an} | RED CARD {mt} {pn}\n{lg}\n{FOLLOW}",img): st["red"][rid]=1;posted+=1

  # PENALTY - VIRAL
  for pn,mt in pl:
   if pn.lower() in BADP: continue
   pid=eid+"_pen_"+pn+"_"+mt
   if pid not in st["pen"]:
    img=mk_text(hn,an,f"{hs}-{as_}",lg,f"PEN {mt}",f"{pn} PEN",pen=True)
    if post(f"{hn} {hs}-{as_} {an} | PENALTY {mt} {pn}\n{lg}\nWill he score? 👇\n{FOLLOW}",img): st["pen"][pid]=1;posted+=1

  # HT/FT ONLY BIG GAMES
  if is_big and status=="STATUS_HALFTIME" and eid not in st["ht"]:
   img=mk_text(hn,an,f"{hs}-{as_}",lg,"HT","HALFTIME")
   if post(f"{hn} {hs}-{as_} {an} | HALFTIME\n{lg}\n{FOLLOW}",img): st["ht"][eid]=1;posted+=1
  if is_big and status=="STATUS_FINAL" and eid not in st["ft"]:
   img=mk_text(hn,an,f"{hs}-{as_}",lg,"FT","FULL TIME")
   if post(f"{hn} {hs}-{as_} {an} | FULL TIME\n{lg}\nFollow for next live! 👇\n{FOLLOW}",img): st["ft"][eid]=1;posted+=1
 return posted

def main():
 st=load();tot=0
 for i in range(10):
  print(f"LOOP {i+1}");tot+=run_once(st);save(st)
  if i<9: time.sleep(5)
 # NEWS FOOTBALL ONLY WITH PHOTO
 if time.time()-st.get("last_news_time",0)>900:
  news=fetch_news();random.shuffle(news)
  for n in news[:20]:
   ttl=n["title"][:80]
   if ttl.lower() in [x.lower() for x in st["news"]]: continue
   real=n.get("hd")
   if not real or real.size[0]<300: continue
   img=mk_news(real)
   cap=f"{n['title']}\n\n{n['desc']}\n\nSource: {n['source']}\n\n#UnfilteredScores #Follow #FootballNews #Viral #FYP"
   if post(cap,img): st["news"].append(ttl);st["last_news_time"]=time.time();tot+=1;break
 print(f"V69 DONE {tot}");save(st)
if __name__=="__main__": main()
