# V63 FINAL 2KPL+9UCL TODAY - BRAND GREEN STAYS - LIVESCORE + NEWS + 100 REQ SAFE
print("V63 BRAND GREEN LIVE")
import os,json,requests,re,random,time,xml.etree.ElementTree as ET
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image,ImageDraw,ImageFont
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
PID=os.getenv("PAGE_ID");TOK=os.getenv("PAGE_ACCESS_TOKEN") or os.getenv("FB_TOKEN")
API_KEY=os.getenv("API_FOOTBALL_KEY")
FILE="posted_state.json";EAT=ZoneInfo("Africa/Nairobi")
NAMES={"eng.1":"Premier League","ken.1":"KPL","uefa.champions":"UCL","uefa.europa":"Europa League"}
PR=["eng.1","ken.1","uefa.champions","esp.1","ita.1"]
BRAND_GREEN=(0,255,100); BRAND_BLACK=(0,0,0)

USED=0;LIMIT=75 # save 25 for 9 UCL late
def api(path):
 global USED
 if not API_KEY: return None
 if USED>=LIMIT: print(f"API STOP {USED}/100"); return None
 try:
  r=requests.get(f"https://v3.football.api-sports.io/{path}",headers={"x-apisports-key":API_KEY},timeout=7)
  if r.status_code==200: USED+=1; print(f"API {USED}/100 {path}"); return r.json()
 except Exception as e: print(f"API ERR {e}")
 return None

def load():
 d={"lineup":{},"goals":{},"ht":{},"ft":{},"last":{},"red":{},"kick":{},"news":[],"last_news_time":0,"api_lineup":{}}
 try:
  with open(FILE) as f:
   s=json.load(f)
   for k in d: s.setdefault(k,d[k]); return s
 except: return d
def save(s): open(FILE,"w").write(json.dumps(s))
def dl(u):
 try:
  r=requests.get(u,timeout=8,headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.sofascore.com/"})
  if r.status_code==200 and len(r.content)>3000: return Image.open(BytesIO(r.content)).convert("RGBA")
 except:0
 return None
def scorer_face(n):
 if not n or len(n)<3: return None
 if n.lower() in ["lens","sporting cp","slavia praha","sporting","rc lens","goal scorer","sporting"]: return None
 try:
  j=requests.get("https://api.sofascore.app/api/v1/search/all?q="+n,timeout=5,headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.sofascore.com/"}).json()
  for r in j.get("results",[]):
   if r.get("type")=="player":
    nid=r.get("entity",{}).get("id")
    if nid:
     im=dl(f"https://api.sofascore.app/api/v1/player/{nid}/image")
     if im: return im
 except:0
 return None
def real_img(eid,code,h,a):
 try:
  j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/summary?event={eid}",timeout=5).json()
  for p in j.get("header",{}).get("pics",[]):
   u=p.get("href") or p.get("url")
   if u:
    im=dl(u)
    if im and im.size[0]>400: return im
 except:0
 for tm in [h,a]:
  try:
   j=requests.get(f"https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t={tm}",timeout=5).json()
   t=(j.get("teams") or [None])[0]
   if t:
    for k in ["strStadiumThumb","strTeamFanart1","strTeamBanner"]:
     u=t.get(k)
     if u and "http" in u:
      im=dl(u)
      if im and im.size[0]>250: return im
  except:0
 for tm in [h,a]:
  try:
   sj=requests.get(f"https://api.sofascore.app/api/v1/search/all?q={tm}",timeout=4,headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.sofascore.com/"}).json()
   for r in sj.get("results",[])[:2]:
    if r.get("type")=="team":
     tid=r.get("entity",{}).get("id")
     if tid:
      im=dl(f"https://api.sofascore.app/api/v1/team/{tid}/image")
      if im: return im
  except:0
 try:
  im=dl(f"https://picsum.photos/seed/{h[:3]}{a[:3]}/1080/1350")
  if im: return im
 except:0
 return None
def bg_real(h,g):
 W,H=1080,1350
 if g:
  try:
   bg=g.convert("RGB").resize((W,H),Image.LANCZOS)
   ov=Image.new("RGB",(W,H),(0,0,0)); return Image.blend(bg,ov,0.45)
  except:0
 return None
def post(msg,path):
 try:
  r=requests.post(f"https://graph.facebook.com/v20.0/{PID}/photos",data={"caption":msg,"access_token":TOK},files={"source":open(path,"rb")},timeout=20)
  print(f"FB {r.status_code}");return r.status_code==200
 except Exception as e: print(f"FB ERR {e}");return False
def mk(h,a,sc,lg,top,bot,g,face=None,red=False):
 W,H=1080,1350
 bg=bg_real(h,g)
 if bg is None and face:
  try: bg=face.convert("RGB").resize((W,H),Image.LANCZOS);bg=Image.blend(bg,Image.new("RGB",(W,H),(0,0,0)),0.5)
  except:0
 if bg is None: bg=Image.new("RGB",(W,H),(12,12,12))
 d=ImageDraw.Draw(bg)
 try: fb=ImageFont.truetype("DejaVuSans-Bold.ttf",90);fs=ImageFont.truetype("DejaVuSans-Bold.ttf",34);fs2=ImageFont.truetype("DejaVuSans-Bold.ttf",28)
 except: fb=fs=fs2=ImageFont.load_default()
 # BRAND GREEN ALWAYS
 header_col=BRAND_GREEN if not red else (255,0,0)
 d.rounded_rectangle([30,20,W-30,85],radius=20,fill=header_col);d.text((50,30),(f"Unfiltered {lg} {top}")[:44],font=fs,fill=(0,0,0))
 if face:
  try:
   sf=face.resize((400,400),Image.LANCZOS);ms=Image.new("L",(400,400),0);ImageDraw.Draw(ms).ellipse([0,0,400,400],fill=255)
   bg.paste(sf,(340,130),ms,ms);d=ImageDraw.Draw(bg)
  except:0
 d.rounded_rectangle([280,700,800,830],radius=30,fill=(255,255,255));d.text((340,720),sc,font=fb,fill=(0,0,0))
 d.rounded_rectangle([30,1240,W-30,1320],radius=20,fill=header_col);d.text((40,1252),bot[:56],font=fs2,fill=(0,0,0))
 p="/tmp/m.png";bg.save(p,quality=95);return p
def mk_lineup(h,a,lg,dtxt,g):
 W,H=1080,1350
 bg=bg_real(h,g)
 if bg is None: bg=Image.new("RGB",(W,H),(15,15,15))
 d=ImageDraw.Draw(bg)
 try: fs=ImageFont.truetype("DejaVuSans-Bold.ttf",30)
 except: fs=ImageFont.load_default()
 d.rounded_rectangle([30,20,W-30,85],radius=20,fill=BRAND_GREEN);d.text((50,30),f"Unfiltered {lg} LINEUP"[:42],font=fs,fill=(0,0,0))
 d.rounded_rectangle([30,110,W-30,1320],radius=25,fill=(0,0,0));d.text((50,130),f"{h} vs {a}\n\n{dtxt}"[:750],font=fs,fill=(255,255,255))
 p="/tmp/line.png";bg.save(p,quality=95);return p
def mk_news(real):
 W,H=1080,1350
 try:
  rw,rh=real.size;max_h=H-90;ratio=min(W/rw,max_h/rh);nw=int(rw*ratio);nh=int(rh*ratio);fg=real.resize((nw,nh),Image.LANCZOS)
  bg=Image.new("RGB",(W,H),(0,0,0));bg.paste(fg,((W-nw)//2,85+(max_h-nh)//2))
 except: bg=Image.new("RGB",(W,H),(0,0,0))
 d=ImageDraw.Draw(bg,"RGBA")
 try: fs=ImageFont.truetype("DejaVuSans-Bold.ttf",36)
 except: fs=ImageFont.load_default()
 d.rounded_rectangle([15,15,W-15,80],radius=20,fill=BRAND_GREEN);d.text((35,28),"Unfiltered Scores 🟢",font=fs,fill=(0,0,0))
 p="/tmp/news.png";bg.save(p,quality=100);return p
def get_hd(u):
 try:
  r=requests.get(u,timeout=7,headers={"User-Agent":"Mozilla/5.0"})
  m=re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',r.text,re.I)
  if m:
   uu=m.group(1)
   if uu.startswith("//"): uu="https:"+uu
   im=dl(uu)
   if im and im.size[0]>300: return im
 except:0
 return None
def get_sb(lg):
 try:
  j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/scoreboard",timeout=5).json()
  ev=[]
  for e in j.get("events",[]): e["_code"]=lg;e["_lname"]=NAMES.get(lg,lg);ev.append(e)
  return ev
 except: return []
def get_livescore():
 ev=[]
 try:
  r=requests.get("https://prod-public-api.livescore.com/v1/events/list?category=soccer",timeout=6,headers={"User-Agent":"Mozilla/5.0"})
  j=r.json()
  for stage in j.get("Stages",[]):
   comp=stage.get("Cnm",""); lg="KPL" if "kenya" in comp.lower() else "UCL" if "champions" in comp.lower() else None
   if not lg: continue
   code="ken.1" if lg=="KPL" else "uefa.champions"
   for e in stage.get("Events",[]):
    try:
     h=e.get("T1",[{}])[0].get("Nm","");a=e.get("T2",[{}])[0].get("Nm","")
     hs=str(e.get("Tr1","0"));ass=str(e.get("Tr2","0"));st=e.get("Eps","")
     st_map={"In Progress":"STATUS_IN_PROGRESS","HT":"STATUS_HALFTIME","FT":"STATUS_FINAL"}
     stype=st_map.get(st,"STATUS_SCHEDULED")
     ev.append({"id":f"ls_{e.get('Eid')}","_code":code,"_lname":lg,"competitions":[{"status":{"type":{"name":stype,"shortDetail":st}},"competitors":[{"homeAway":"home","team":{"displayName":h},"score":hs},{"homeAway":"away","team":{"displayName":a},"score":ass}],"date":""}]})
    except:0
 except:0
 return ev
def get_fast():
 ev=[];H={"User-Agent":"Mozilla/5.0","Referer":"https://www.sofascore.com/"}
 try:
  r=requests.get("https://api.sofascore.app/api/v1/sport/football/events/live",timeout=7,headers=H)
  j=r.json()
  for e in j.get("events",[]):
   try:
    tour=(e.get("tournament",{}).get("name","")+e.get("tournament",{}).get("category",{}).get("name","")).lower()
    code=None;lname=None
    if "kenya" in tour: code="ken.1";lname="KPL"
    elif "champions" in tour: code="uefa.champions";lname="UCL"
    elif "premier league" in tour: code="eng.1";lname="Premier League"
    if not code: continue
    hs=str(e.get("homeScore",{}).get("current",0));ass=str(e.get("awayScore",{}).get("current",0))
    st=e.get("status",{}).get("type","");st_map={"inprogress":"STATUS_IN_PROGRESS","halftime":"STATUS_HALFTIME","finished":"STATUS_FINAL"}
    stype=st_map.get(st,"STATUS_SCHEDULED");mn=e.get("time",{}).get("minute",0)
    ev.append({"id":"sofa_"+str(e.get('id')),"_code":code,"_lname":lname,"competitions":[{"status":{"type":{"name":stype,"shortDetail":f"{mn}'"}},"competitors":[{"homeAway":"home","team":{"displayName":e.get("homeTeam",{}).get("name","")},"score":hs},{"homeAway":"away","team":{"displayName":e.get("awayTeam",{}).get("name","")},"score":ass}],"date":""}]})
   except:0
 except:0
 return ev
def get_sum(ar):
 eid,code=ar
 try:
  j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/summary?event={eid}",timeout=5).json()
  return {"d":j.get("header",{}).get("competitions",[{}])[0].get("details",[]) or [],"l":j.get("lineups") or []}
 except: return {"d":[],"l":[]}
def fast_inc(h,a):
 g=[];r=[]
 try:
  j=requests.get(f"https://api.sofascore.app/api/v1/search/all?q={h} {a}",timeout=4,headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.sofascore.com/"}).json()
  for res in j.get("results",[])[:2]:
   if res.get("type")=="event":
    sid=res.get("entity",{}).get("id")
    if not sid: continue
    inc=requests.get(f"https://api.sofascore.app/api/v1/event/{sid}/incidents",timeout=4,headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.sofascore.com/"}).json()
    for it in inc.get("incidents",[])[:25]:
     tp=it.get("incidentType","");pn=it.get("player",{}).get("name","");mn=it.get("time",0);pid=it.get("player",{}).get("id")
     if not pn or len(pn)<3: continue
     if pn.lower() in [h.lower(), a.lower(), "lens","sporting cp","slavia praha"]: continue
     ph=None
     if pid:
      try: ph=dl(f"https://api.sofascore.app/api/v1/player/{pid}/image")
      except:0
     if tp=="goal": g.append((pn,f"{mn}'",ph,it))
     if tp=="card" and it.get("incidentClass")=="red": r.append((pn,f"{mn}'",ph,it))
    if g or r: break
 except:0
 return g,r
def get_api_all_live():
 j=api("fixtures?live=all")
 ev=[]
 if not j: return ev
 for f in j.get("response",[]):
  try:
   league=f["league"]["name"].lower()
   if "kenya" in league: lname="KPL";code="ken.1"
   elif "champions league" in league: lname="UCL";code="uefa.champions"
   elif "premier league" in league: lname="Premier League";code="eng.1"
   else: continue
   h=f["teams"]["home"]["name"];a=f["teams"]["away"]["name"]
   hs=str(f["goals"]["home"] or 0);ass=str(f["goals"]["away"] or 0)
   st=f["fixture"]["status"]["short"]
   st_map={"1H":"STATUS_IN_PROGRESS","2H":"STATUS_IN_PROGRESS","HT":"STATUS_HALFTIME","FT":"STATUS_FINAL","NS":"STATUS_SCHEDULED"}
   stype=st_map.get(st,"STATUS_SCHEDULED")
   ev.append({"id":f"apif_{f['fixture']['id']}","_code":code,"_lname":lname,"_apif_id":f["fixture"]["id"],"competitions":[{"status":{"type":{"name":stype,"shortDetail":st}},"competitors":[{"homeAway":"home","team":{"displayName":h},"score":hs},{"homeAway":"away","team":{"displayName":a},"score":ass}],"date":f["fixture"]["date"]}]})
  except:0
 print(f"API LIVE {len(ev)}")
 return ev
def get_api_details(apif_id):
 line=None;events=None
 j1=api(f"fixtures/lineups?fixture={apif_id}")
 if j1 and j1.get("response"): line=j1["response"]
 j2=api(f"fixtures/events?fixture={apif_id}")
 if j2 and j2.get("response"): events=j2["response"]
 return line,events
def fetch_news():
 BAD=["rugby","cricket","tennis","golf","boxing"]
 news=[]
 print("FETCH NEWS LIVESCORE")
 try:
  r=requests.get("https://www.livescore.com/en/news/category/premier-league/",timeout=7,headers={"User-Agent":"Mozilla/5.0"})
  links=re.findall(r'href="(/en/news/[^"]+)"',r.text)[:10]
  for lnk in links:
   url="https://www.livescore.com"+lnk
   hd=get_hd(url)
   if hd:
    ttl=lnk.split("/")[-2].replace("-"," ")[:80]
    news.append({"title":ttl.title(),"link":url,"desc":ttl[:200],"source":"LiveScore","hd":hd})
 except:0
 try:
  j=requests.get("https://site.api.espn.com/apis/site/v2/sports/soccer/news",timeout=7).json()
  for a in j.get("articles",[])[:10]:
   ttl=a.get("headline","");ims=a.get("images",[]);img=ims[0].get("url") if ims else None
   if ttl and img and not any(b in ttl.lower() for b in BAD):
    im=dl(img)
    if im: news.append({"title":ttl,"link":a.get("links",{}).get("web",{}).get("href",""),"desc":a.get("description","")[:200],"source":"ESPN","hd":im})
 except:0
 return news
def run_once(st):
 all_ev=[]
 with ThreadPoolExecutor(max_workers=10) as ex:
  for lst in ex.map(get_sb,PR): all_ev.extend(lst)
 all_ev.extend(get_fast())
 all_ev.extend(get_livescore())
 all_ev.extend(get_api_all_live())
 live=[e for e in all_ev if e["competitions"][0]["status"]["type"]["name"] in ["STATUS_IN_PROGRESS","STATUS_HALFTIME","STATUS_SCHEDULED","STATUS_FINAL"]]
 print(f"LIVE {len(live)}")
 sums={}
 with ThreadPoolExecutor(max_workers=12) as ex:
  ids=[(e["id"],e["_code"]) for e in live if not str(e["id"]).startswith("sofa_") and not str(e["id"]).startswith("ls_") and not str(e["id"]).startswith("apif_")]
  evs=[e for e in live if not str(e["id"]).startswith("sofa_") and not str(e["id"]).startswith("ls_") and not str(e["id"]).startswith("apif_")]
  for e,s in zip(evs, ex.map(get_sum, ids)): sums[e["id"]]=s
 posted=0
 for ev in live:
  eid=ev["id"];code=ev["_code"];comp=ev["competitions"][0];status=comp["status"]["type"]["name"];short=comp["status"]["type"].get("shortDetail","")
  comps=comp["competitors"]
  try: h=next(x for x in comps if x["homeAway"]=="home");a=next(x for x in comps if x["homeAway"]=="away")
  except: continue
  hn,an=h["team"]["displayName"],a["team"]["displayName"];hs,as_=str(h.get("score","0")),str(a.get("score","0"));lg=ev["_lname"]
  tag="#KPL #FKFPL #ViralKE 🟢" if lg=="KPL" else "#UCL #ChampionsLeague #Viral 🟢"
  summ=sums.get(eid,{"d":[],"l":[]});details=summ["d"]
  m=re.search(r"(\d+)'",short);minute=int(m.group(1)) if m else 0
  ground=real_img(eid if not str(eid).startswith("sofa_") and not str(eid).startswith("ls_") and not str(eid).startswith("apif_") else "0",code,hn,an)
  try:
   ds=comp.get("date","");dt=datetime.fromisoformat(ds.replace("Z","+00:00")).astimezone(EAT) if ds else datetime.now(EAT)
   df=dt.strftime("%a %d %b");tf=dt.strftime("%I:%M %p")
  except: df=tf="";dt=datetime.now(EAT)
  if status=="STATUS_SCHEDULED" and eid not in st["lineup"]:
   try:
    hrs=(dt - datetime.now(EAT)).total_seconds()/3600 if ds else 10
    if 0<=hrs<=4:
     apif_id=ev.get("_apif_id");txt=""
     if apif_id and eid not in st["api_lineup"]:
      line,evts=get_api_details(apif_id)
      if line:
       for lu in line[:2]:
        tn=lu["team"]["name"];txt+=tn+":\n"
        for ath in lu.get("startXI",[])[:11]: txt+=ath["player"]["name"]+", "
        txt+="\n\n"
       st["api_lineup"][eid]=1
     if not txt:
      lineups=summ.get("l",[])
      if lineups and len(lineups)>=2:
       for lu in lineups[:2]:
        tn=lu.get("team",{}).get("displayName","Team");txt+=tn+":\n"
        for ath in lu.get("athletes",[])[:11]: txt+=ath.get("athlete",{}).get("displayName","")+", "
        txt+="\n\n"
     if len(txt)>50:
      img=mk_lineup(hn,an,lg,txt,ground)
      if img and post(f"LINEUP! 🟢 {hn} vs {an}\n\n{lg}\n{df} {tf} EAT\n\n{txt[:500]}\n\nWho wins? 👇\n\n{tag}",img):
       st["lineup"][eid]=1;posted+=1
   except Exception as e: print(f"LINEUP ERR {e}")
  gl,rl=fast_inc(hn,an)
  api_pname=None;api_min=None;api_face=None;api_red=[]
  if ev.get("_apif_id") and (hs+"-"+as_)!=st.get("last",{}).get(eid,"0-0"):
   _,evts=get_api_details(ev["_apif_id"]) if USED<LIMIT else (None,None)
   if evts:
    for e in evts[-5:]:
     if e.get("type")=="Goal" and not api_pname:
      api_pname=e.get("player",{}).get("name","");api_min=str(e.get("time",{}).get("elapsed",0))+"'"
      api_face=scorer_face(api_pname)
     if e.get("type")=="Card" and e.get("detail")=="Red Card":
      pn=e.get("player",{}).get("name","");mn=str(e.get("time",{}).get("elapsed",0))+"'"
      api_red.append((pn,mn,scorer_face(pn),None))
  last=st.get("last",{}).get(eid,"0-0")
  if status in ["STATUS_IN_PROGRESS","STATUS_HALFTIME"] and last!=hs+"-"+as_:
   if not (last=="0-0" and hs=="0" and as_=="0"):
    gid=eid+"_"+hs+"-"+as_
    if gid not in st["goals"]:
     pname="";mt=f"{minute}'" if minute>0 else "Live";face=None
     for d in details[-5:]:
      if "goal" in str(d.get("type","")).lower():
       cand=d.get("athlete",{}).get("displayName","")
       if cand and len(cand)>2 and cand.lower() not in [hn.lower(), an.lower()]: pname=cand;break
     if gl:
      for pn,mt2,fc,_ in reversed(gl):
       if pn and len(pn)>2 and pn.lower() not in [hn.lower(), an.lower()]: pname=pn;mt=mt2 if mt2!="0'" else mt;face=fc;break
     if api_pname: pname=api_pname;mt=api_min;face=api_face
     if not pname or len(pname)<3 or "goal scorer" in pname.lower() or pname.lower() in [hn.lower(), an.lower(), "lens"]:
      print(f"SKIP GOAL invalid '{pname}'")
     else:
      if not face: face=scorer_face(pname)
      img=mk(hn,an,hs+"-"+as_,lg,mt+" GOAL",mt+" "+pname,ground,face)
      if img and post(f"GOAL! 🟢 {mt} {pname} scores!\n\n{lg}\n{hn} {hs}-{as_} {an}\n\n{tag}",img):
       st["goals"][gid]=1;posted+=1
  st["last"][eid]=hs+"-"+as_
  for pn,mt,fc,_ in rl+api_red:
   if not pn or pn.lower() in [hn.lower(), an.lower()]: continue
   rid=eid+"_red_"+pn+"_"+mt
   if rid not in st["red"]:
    if not fc: fc=scorer_face(pn)
    img=mk(hn,an,hs+"-"+as_,lg,"RED "+mt,"RED "+pn,ground,fc,True)
    if img and post(f"RED CARD! 🟢 {mt} {pn} sent off!\n\n{lg}\nScore: {hn} {hs}-{as_} {an}\n\n{tag}",img):
     st["red"][rid]=1;posted+=1
  if status=="STATUS_HALFTIME" and eid not in st["ht"]:
   img=mk(hn,an,hs+"-"+as_,lg,"HT","HALFTIME",ground)
   if img and post(f"HALFTIME 🟢\n\n{lg}\n{hn} {hs}-{as_} {an}\n\n{tag}",img): st["ht"][eid]=1;posted+=1
  if status=="STATUS_FINAL" and eid not in st["ft"]:
   img=mk(hn,an,hs+"-"+as_,lg,"FT","FULL TIME",ground)
   if img and post(f"FULL TIME 🟢\n\n{lg}\n{hn} {hs}-{as_} {an}\n\n{tag}",img): st["ft"][eid]=1;posted+=1
 return posted
def main():
 print(f"V63 MAIN API USED {USED}");st=load();tot=0
 for i in range(5):
  print(f"LOOP {i+1} API {USED}/{LIMIT}");tot+=run_once(st);save(st)
  if i<4: time.sleep(12)
 now=datetime.now().timestamp()
 if now-st.get("last_news_time",0)>700:
  news=fetch_news();random.shuffle(news)
  for n in news[:20]:
   ttl=n["title"][:80]
   if ttl.lower() in [x.lower() for x in st["news"]]: continue
   if len(ttl)<15: continue
   real=n.get("hd")
   if not real or real.size[0]<300: continue
   img=mk_news(real)
   cap=f"{n['title']}\n\n{n['desc']}\n\nSource: {n['source']}\n\nFollow Unfiltered Scores for live KPL + 9 UCL tonight! 🟢\n\n#FootballNews #KPL #UCL #Viral"
   if post(cap,img): st["news"].append(ttl);st["last_news_time"]=now;tot+=1;break
 print(f"V63 DONE {tot} API USED {USED}");save(st)
if __name__=="__main__": main()
