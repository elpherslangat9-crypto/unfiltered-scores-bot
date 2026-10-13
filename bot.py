# V55 GLOBAL FAST - SYNTAX FIXED - TESTED
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
    except: bg=Image.new("RGB",(W,H),(0,0,0))
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
def get_global_fast_live():
    ev=[]
    try:
        j=requests.get("https://api.sofascore.app/api/v1/sport/football/events/live",timeout=6,headers={"User-Agent":"Mozilla/5.0"}).json()
        for e in j.get("events",[]):
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
            if not code and any(x in hn_low+" "+an_low for x in ["gor mahia","leopards","tusker","shabana","kcb","bandari","homeboyz","muranga","city stars","mara sugar","bidco"]):
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
    except Exception as ex:
        print("GLOBAL FAST ERR "+str(ex))
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
def fetch_news():
    news=[]
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
 try:
    fast_all=get_global_fast_live()
    if fast_all:
        print("FAST TOTAL "+str(len(fast_all)))
        all_ev.extend(fast_all)
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
     cap_text = "LINEUP "+lg+"\n\n"+hn+" vs "+an+"\n\n"+df+" "+tf+" EAT\n\n"+txt+"\nWho wins?\n\n"+tag
     if post(cap_text,p):
      st.setdefault("lineup",{})[eid]=1; posted+=1
  if status=="STATUS_IN_PROGRESS" and eid not in st.get("kick",{}):
   if minute<=10:
    img=mk_img(hn,an,"0-0",lg,"KICK OFF","KICK OFF "+hn+" vs "+an,ground)
    cap_text = "KICK OFF! "+lg+"\n\n"+hn+" vs "+an+"\n\n"+df+" "+tf+" EAT\n\nPredict!\n\n"+tag
    if post(cap_text,img):
     st.setdefault("kick",{})[eid]=1; posted+=1
  gl,rl,pml,pgl,varl=fast_inc_all(hn,an)
  last=st.get("last",{}).get(eid,"0-0")
  # FIXED LINE 400 - Added colon
  if status in ["STATUS_IN_PROGRESS","STATUS_HALFTIME"] and last!=hs+"-"+as_:
   if not (last=="0-0" and hs=="0" and as_=="0"):
    gid=eid+"_"+hs+"-"+as_
    if gid not in st.get("goals",{}):
     pname=""; pid=None
     for d in details[-6:]:
      if "goal" in str(d.get("type","")).lower():
       pname=d.get("athlete",{}).get("displayName",""); pid=d.get("athlete",{}).get("id"); break
     face=None; mt=str(minute)+"'"; is_pen=False
     if gl:
      pn,mt,fc,it=gl[-1]
      if pn: pname=pn; face=fc
      if it and "penalty" in str(it).lower(): is_pen=True
     if not face and pname: face=scorer_face(pname,pid)
     if not pname: pname=hn
     label="PENALTY" if is_pen else mt+" GOAL"
     img=mk_img(hn,an,hs+"-"+as_,lg,label,label+" "+pname,ground,face)
     cap_text = "GOAL! "+label+"! "+mt+" "+pname+" scores!\n\n"+lg+"\n"+hn+" "+hs+"-"+as_+" "+an+"\n\nCurrent Score: "+hn+" "+hs+" - "+as_+" "+an+"\n\n"+tag
     if post(cap_text,img):
      st.setdefault("goals",{})[gid]=1; posted+=1
  st.setdefault("last",{})[eid]=hs+"-"+as_
  for pn,mt,fc,it in rl:
   rid=eid+"_red_"+pn+"_"+mt
   if rid not in st.get("red",{}):
    if not fc: fc=scorer_face(pn)
    img=mk_img(hn,an,hs+"-"+as_,lg,"RED "+mt,"RED "+pn,ground,fc,True)
    cap_text = "RED CARD! "+mt+" "+pn+" sent off!\n\n"+lg+"\nScore: "+hn+" "+hs+"-"+as_+" "+an+"\n\n"+tag
    if post(cap_text,img):
     st.setdefault("red",{})[rid]=1; posted+=1
  for pn,mt,fc,it in pml:
   rid=eid+"_pmiss_"+pn+"_"+mt
   if rid not in st.get("pen_miss",{}):
    if not fc: fc=scorer_face(pn)
    img=mk_img(hn,an,hs+"-"+as_,lg,"MISSED PEN "+mt,"MISSED PEN "+pn,ground,fc,False,True)
    cap_text = "MISSED PENALTY! "+mt+" "+pn+" misses!\n\n"+lg+"\n"+hn+" "+hs+"-"+as_+" "+an+"\n\n"+tag
    if post(cap_text,img):
     st.setdefault("pen_miss",{})[rid]=1; posted+=1
  for pn,mt,fc,it in pgl:
   rid=eid+"_pgoal_"+pn+"_"+mt
   if rid not in st.get("pen_goal",{}):
    if not fc: fc=scorer_face(pn)
    img=mk_img(hn,an,hs+"-"+as_,lg,"PENALTY "+mt,"PENALTY "+pn,ground,fc)
    cap_text = "PENALTY GOAL! "+mt+" "+pn+" converts!\n\n"+lg+"\nScore: "+hn+" "+hs+"-"+as_+" "+an+"\n\n"+tag
    if post(cap_text,img):
     st.setdefault("pen_goal",{})[rid]=1; posted+=1
  for pn,mt,fc,it in varl:
   rid=eid+"_var_"+pn+"_"+mt
   if rid not in st.get("var",{}):
    if not fc and pn: fc=scorer_face(pn)
    img=mk_img(hn,an,hs+"-"+as_,lg,"VAR "+mt,"VAR CHECK "+pn,ground,fc,False,True)
    cap_text = "VAR CHECK! "+mt+" "+pn+"\n\n"+lg+"\n"+hn+" "+hs+"-"+as_+" "+an+"\n\nGoal or no?\n\n"+tag
    if post(cap_text,img):
     st.setdefault("var",{})[rid]=1; posted+=1
  if status=="STATUS_HALFTIME" and eid not in st.get("ht",{}):
   img=mk_img(hn,an,hs+"-"+as_,lg,"HT","HALFTIME",ground)
   cap_text = "HALFTIME\n\n"+lg+"\n"+hn+" "+hs+"-"+as_+" "+an+"\n\n"+tag
   if post(cap_text,img):
    st.setdefault("ht",{})[eid]=1; posted+=1
  if status=="STATUS_FINAL" and eid not in st.get("ft",{}):
   img=mk_img(hn,an,hs+"-"+as_,lg,"FT","FULL TIME",ground)
   cap_text = "FULL TIME\n\n"+lg+"\n"+hn+" "+hs+"-"+as_+" "+an+"\n\n"+tag
   if post(cap_text,img):
    st.setdefault("ft",{})[eid]=1; posted+=1
 return posted
def main():
 st=load(); tot=0
 for i in range(6):
  tot+=run_once(st); save(st)
  if i<5: time.sleep(10)
 print("V55 FIXED DONE "+str(tot)); save(st)
if __name__=="__main__":
 main()
