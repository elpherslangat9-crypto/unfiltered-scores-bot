import os,json,time,requests,re
from datetime import datetime,timezone,timedelta
from io import BytesIO
from PIL import Image,ImageDraw,ImageFont
import feedparser
FB_TOKEN=os.getenv("FB_TOKEN","").strip();FB_PAGE_ID=os.getenv("FB_PAGE_ID","1293090263895541").strip();STATE_FILE="state.json";RECENT_HOURS=3
def load_state():
 try:return json.load(open(STATE_FILE))
 except:return {"posted":[]}
def save_state(s):
 try:json.dump(s,open(STATE_FILE,"w"))
 except:pass
state=load_state()
def safe_list(x):return x if isinstance(x,list) else [x] if isinstance(x,dict) else [] if not x else [x]
def is_recent(d):
 try:return (datetime.now(timezone.utc)-datetime.fromisoformat(d.replace("Z","+00:00")))<timedelta(hours=5)
 except:return True
LEAGUES=["eng.1","eng.2","esp.1","ita.1","ger.1","fra.1","ned.1","por.1","ken.1","rsa.1","caf.champions","caf.confed","uefa.champions","uefa.europa","fifa.worldq"]
ESPN=[f"https://site.api.espn.com/apis/site/v2/sports/soccer/{c}/scoreboard" for c in LEAGUES]
NON=["darts","snooker","cricket","rugby","tennis","nba","nfl","golf","f1","boxing","mma","ufc"];MUST=["football","premier","arsenal","chelsea","liverpool","man","tottenham","barcelona","real","atletico","bayern","psg","juventus","milan","serie","liga","bundes","champions","europa","fa cup","transfer","goal","striker","manager","kpl","gor","shabana","tusker","leopards"];HT="\n\n#football #unfilteredscores"
def is_fb(t):
 t=t.lower()
 if any(b in t for b in NON):return False
 return any(g in t for g in MUST)
def fetch_json(u):
 try:
  r=requests.get(u,timeout=12,headers={"User-Agent":"Mozilla/5.0"})
  if r.status_code==200:return r.json()
 except:pass
def get_score(comps):
 try:h=next((c for c in comps if c.get("homeAway")=="home"),comps[0]);a=next((c for c in comps if c.get("homeAway")=="away"),comps[1]);return int(h.get("score")or 0),int(a.get("score")or 0)
 except:return 0,0
def font(s,b=0):
 try:return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if b else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",s)
 except:return ImageFont.load_default()
def make_hd(lines):
 W,H=1280,720;img=Image.new("RGB",(W,H),(8,12,28));d=ImageDraw.Draw(img)
 for y in range(H):d.line([(0,y),(W,y)],fill=(int(8+y*0.12),int(12+y*0.18),int(28+y*0.25)))
 bb=font(60,1);bm=font(38,1);bs=font(20,1);y=100
 for i,ln in enumerate(lines[:4]):f=bb if i==0 else bm;d.text((55,y),ln[:55],font=f,fill=(255,255,255));y+=88
 bw,bh=300,38;bx=(W-bw)//2;d.rounded_rectangle([bx,H-55,bx+bw,H-55+bh],radius=19,fill=(0,215,95));d.text((bx+26,H-47),"UNFILTERED SCORES",font=bs,fill=(255,255,255));b=BytesIO();img.save(b,format="JPEG",quality=97);b.seek(0);return b
def fetch_lineups(eid):
 for lu in ESPN:
  try:
   code=lu.split("/soccer/")[1].split("/scoreboard")[0];data=fetch_json(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/summary?event={eid}")
   if not data:continue
   ros=data.get("rosters",[])
   if len(ros)<2:continue
   res={"home":{"xi":[],"bench":[]},"away":{"xi":[],"bench":[]}}
   for idx,r in enumerate(ros[:2]):
    k="home" if idx==0 else "away";ap=[]
    for aa in r.get("roster",[]):
     if not isinstance(aa,dict):continue
     ath=aa.get("athlete",{});nm=ath.get("displayName")or aa.get("displayName","")
     if not nm:continue
     ap.append({"n":nm,"j":str(aa.get("jersey","")or ""),"s":aa.get("starter")})
    has=sum(1 for x in ap if x["s"]is not None)
    xi=[x for x in ap if x["s"]] if has else ap[:11];bn=[x for x in ap if not x["s"]] if has else ap[11:18]
    res[k]["xi"]=xi[:11];res[k]["bench"]=bn[:7]
   if len(res["home"]["xi"])>=7 and len(res["away"]["xi"])>=7:return res
  except:continue
def make_lineup(h,a,ld,logos=None):
 W,H=1080,1150;img=Image.new("RGB",(W,H),(12,20,40));d=ImageDraw.Draw(img,"RGBA")
 for y in range(H):d.line([(0,y),(W,y)],fill=(int(12+y*0.04),int(20+y*0.07),int(42+y*0.1)))
 bb=font(32,1);bm=font(20,1);bs=font(16,1);bt=font(13)
 d.rounded_rectangle([12,10,W-12,92],radius=16,fill=(255,255,255,18))
 li=[]
 if logos:
  for u in logos:
   try:im=Image.open(BytesIO(requests.get(u,timeout=5,headers={"User-Agent":"Mozilla/5.0"}).content)).convert("RGBA").resize((46,46),Image.LANCZOS);li.append(im)
   except:li.append(None)
 if li and li[0]:img.paste(li[0],(18,20),li[0])
 if len(li)>1 and li[1]:img.paste(li[1],(W-66,20),li[1])
 d.text((76,16),f"{h[:16]} vs {a[:16]}",font=bb,fill=(255,255,255));d.text((76,60),"OFFICIAL LINEUPS",font=bt,fill=(0,230,120))
 def card(x,team,dd):
  y0=104;cw=518;ch=H-y0-68;d.rounded_rectangle([x+2,y0+2,x+cw+2,y0+ch+2],radius=18,fill=(0,0,0,60));d.rounded_rectangle([x,y0,x+cw,y0+ch],radius=18,fill=(255,255,255));d.rounded_rectangle([x,y0,x+cw,y0+42],radius=18,fill=(0,200,88));d.rectangle([x,y0+21,x+cw,y0+42],fill=(0,200,88));d.text((x+12,y0+9),team.upper()[:18],font=bm,fill=(255,255,255));y=y0+52
  for i,p in enumerate(dd["xi"][:11]):d.ellipse([x+8,y,x+32,y+24],fill=(0,185,80));num=p.get("j","")or str(i+1);d.text((x+12 if len(num)==1 else x+10,y+2),num[:2],font=bs,fill=(255,255,255));d.text((x+42,y+2),p.get("n","")[:22],font=bs,fill=(15,15,15));y+=32
  d.line([(x+8,y+2),(x+cw-8,y+2)],fill=(0,200,88),width=2);y+=10;d.text((x+10,y),"BENCH:",font=bt,fill=(0,150,60));y+=16
  for b in dd["bench"][:7]:d.text((x+10,y),f"• {b.get('j','')} {b.get('n','')[:20]}".strip(),font=bt,fill=(60,60,60));y+=16
 card(14,h,ld["home"]);card(548,a,ld["away"]);bw,bh=320,36;bx=(W-bw)//2;d.rounded_rectangle([bx,H-46,bx+bw,H-10],radius=18,fill=(0,210,85));d.text((bx+16,H-39),"UNFILTERED SCORES",font=bm,fill=(255,255,255));b=BytesIO();img.save(b,format="JPEG",quality=97);b.seek(0);return b
def make_kick(h,a):
 W,H=1280,720;img=Image.new("RGB",(W,H),(8,14,35));d=ImageDraw.Draw(img)
 for y in range(H):d.line([(0,y),(W,y)],fill=(int(8+y*0.12),int(14+y*0.18),int(35+y*0.25)))
 d.text((80,180),"KICK OFF!",font=font(60,1),fill=(0,230,90));d.text((80,260),h[:30],font=font(32,1),fill=(255,255,255));d.text((80,305),"VS",font=font(22,1),fill=(0,230,90));d.text((80,335),a[:30],font=font(32,1),fill=(255,255,255))
 bw,bh=360,42;bx=(W-bw)//2;d.rounded_rectangle([bx,H-60,bx+bw,H-18],radius=21,fill=(0,218,92));d.text((bx+22,H-52),"UNFILTERED SCORES",font=font(32,1),fill=(255,255,255));b=BytesIO();img.save(b,format="JPEG",quality=96);b.seek(0);return b
def fetch_og(u):
 try:
  t=requests.get(u,timeout=10,headers={"User-Agent":"Mozilla/5.0"}).text
  for pat in [r'property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',r'twitter:image[^>]+content=["\']([^"\']+)["\']']:
   m=re.search(pat,t,re.I)
   if m:
    url=m.group(1);return ("https:"+url if url.startswith("//") else url).replace("/480/","/1280/")
 except:pass
def get_img(e):
 try:
  if hasattr(e,'media_content'):
   for mm in e.media_content:
    if mm.get('url'):return mm['url']
  if hasattr(e,'enclosures') and e.enclosures:
   h=e.enclosures[0].get('href');return h if h and h.startswith("http") else None
  if e.get("link"):return fetch_og(e.get("link"))
 except:pass
def make_real(url):
 try:
  r=requests.get(url,timeout=15,headers={"User-Agent":"Mozilla/5.0"});orig=Image.open(BytesIO(r.content)).convert("RGB");W,H=1280,720;can=Image.new("RGB",(W,H),(0,0,0));iw,ih=orig.size;ra=min(W/iw,H/ih);nw,nh=int(iw*ra),int(ih*ra);rs=orig.resize((nw,nh),Image.LANCZOS);can.paste(rs,((W-nw)//2,(H-nh)//2))
  d=ImageDraw.Draw(can,"RGBA");bw,bh=300,36;bx=(W-bw)//2;d.rounded_rectangle([bx,H-bh-12,bx+bw,H-12],radius=18,fill=(0,210,85,230));d.text((bx+20,H-29),"UNFILTERED SCORES",font=font(20,1),fill=(255,255,255));b=BytesIO();can.save(b,format="JPEG",quality=96);b.seek(0);return b
 except:return None
def make_ft_final(h,a,hs,asc,goals,real_url=None):
 try:
  W,H=1080,1350;can=Image.new("RGB",(W,H),(10,18,42));d=ImageDraw.Draw(can,"RGBA")
  for y in range(H):d.line([(0,y),(W,y)],fill=(int(10+y*0.04),int(18+y*0.06),int(42+y*0.09)))
  th=750 if real_url else 0
  if real_url:
   try:r=requests.get(real_url,timeout=15,headers={"User-Agent":"Mozilla/5.0"});orig=Image.open(BytesIO(r.content)).convert("RGB");iw,ih=orig.size;ra=max(W/iw,th/ih);nw,nh=int(iw*ra),int(ih*ra);rs=orig.resize((nw,nh),Image.LANCZOS);can.paste(rs,((W-nw)//2,0));d.rectangle([0,th-180,W,th+400],fill=(0,0,0,160))
   except:th=0
  yb=th+20 if real_url else 280;bf=font(110,1);bm=font(26,1);bs=font(20,1);bb=font(18,1)
  d.rounded_rectangle([20,yb,W-20,yb+420],radius=20,fill=(0,0,0,70));d.line([(20,yb+2),(W-20,yb+2)],fill=(0,230,90),width=4);d.text((30,yb+18),h[:18].upper(),font=bm,fill=(255,255,255));d.text((W-30,yb+18),a[:18].upper(),font=bm,fill=(255,255,255),anchor="ra");d.text((W//2,yb+90),f"{hs} - {asc}",font=bf,fill=(255,255,255),anchor="mm");d.text((W//2,yb+170),"FT",font=bb,fill=(0,230,90),anchor="mm")
  y1=y2=yb+210
  for g in [x for x in goals if x["team"]=="home"][:6]:d.text((30,y1),f"{g['min']}' {g['scorer'][:20]} {g['extra']}",font=bs,fill=(255,255,255));y1+=32
  for g in [x for x in goals if x["team"]=="away"][:6]:d.text((W-30,y2),f"{g['scorer'][:20]} {g['extra']} {g['min']}'",font=bs,fill=(200,200,200),anchor="ra");y2+=32
  bw,bh=320,38;bx=(W-bw)//2;d.rounded_rectangle([bx,H-50,bx+bw,H-12],radius=19,fill=(0,210,85));d.text((bx+18,H-43),"UNFILTERED SCORES",font=bm,fill=(255,255,255));b=BytesIO();can.save(b,format="JPEG",quality=97);b.seek(0);return b
 except:return None
def post_fb(msg,img):
 if len(FB_TOKEN)<50:return False
 try:r=requests.post(f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos",files={"source":("hd.jpg",img,"image/jpeg")},data={"message":msg,"access_token":FB_TOKEN},timeout=30);return r.status_code==200
 except:return False
def is_posted(k):return k in state.get("posted",[])
def mark(k):p=state.get("posted",[]);p.append(k);state["posted"]=p[-1000:];save_state(state)
def process_live():
 today=datetime.now(timezone.utc).strftime("%Y-%m-%d");cnt=0
 for lu in ESPN:
  data=fetch_json(lu)
  if not data:continue
  for ev in data.get("events",[]):
   try:
    if not ev.get("date","").startswith(today):continue
    comp=ev.get("competitions",[{}])[0];status=comp.get("status",{}).get("type",{}).get("description","");stype=comp.get("status",{}).get("type",{}).get("state","");nstate=comp.get("status",{}).get("type",{}).get("name","");comps=comp.get("competitors",[])
    if len(comps)<2:continue
    home=next((c for c in comps if c.get("homeAway")=="home"),comps[0]);away=next((c for c in comps if c.get("homeAway")=="away"),comps[1]);h=home.get("team",{}).get("displayName","Home");a=away.get("team",{}).get("displayName","Away")
    hl=home.get("team",{}).get("logo","")or (home.get("team",{}).get("logos",[{}])[0].get("href","") if home.get("team",{}).get("logos") else "");al=away.get("team",{}).get("logo","")or (away.get("team",{}).get("logos",[{}])[0].get("href","") if away.get("team",{}).get("logos") else "")
    eid=ev.get("id","");hs,asc=get_score(comps);details=safe_list(comp.get("details",[]))
    if stype=="pre" or "SCHEDULED" in nstate:
     k=f"lineup_{eid}"
     if not is_posted(k):
      ld=fetch_lineups(eid)
      if ld:
       img=make_lineup(h,a,ld,[hl,al]);msg=f"LINEUPS\n{h} vs {a}\n{h}: {', '.join([x['n'][:18] for x in ld['home']['xi'][:11]])}\n{a}: {', '.join([x['n'][:18] for x in ld['away']['xi'][:11]])}\nWho wins?{HT}"
       if post_fb(msg,img):mark(k);cnt+=1
    if stype=="in":
     k=f"kickoff_{eid}"
     if not is_posted(k):
      if post_fb(f"KICK OFF!\n{h} vs {a}\nLIVE NOW!{HT}",make_kick(h,a)):mark(k);cnt+=1
     for d in details:
      if not isinstance(d,dict):continue
      did=d.get("id","")
      if not did:continue
      t=d.get("type",{}).get("text","") if isinstance(d.get("type",{}),dict) else ""
      inv=safe_list(d.get("athletesInvolved",[]));sc=inv[0].get("displayName","") if inv and isinstance(inv[0],dict) else "";mn=d.get("clock",{}).get("displayValue","") if isinstance(d.get("clock",{}),dict) else "";tl=t.lower()
      mp={"Goal":(f"goal_{eid}_{did}",f"GOAL! {mn}'\n{h} {hs}-{asc} {a}\nScorer: {sc}"),"Own Goal":(f"owngoal_{eid}_{did}",f"OWN GOAL! {mn}'\n{h} {hs}-{asc} {a}\nBy {sc}"),"Penalty - Scored":(f"pen_{eid}_{did}",f"PENALTY! {mn}'\n{h} {hs}-{asc} {a}\nScorer: {sc}"),"Penalty - Missed":(f"penmiss_{eid}_{did}",f"PENALTY MISSED! {mn}'\n{h} {hs}-{asc} {a}\n{sc}"),"Red Card":(f"red_{eid}_{did}",f"RED CARD! {mn}'\n{h} {hs}-{asc} {a}\n{sc}"),"Yellow-Red Card":(f"red_{eid}_{did}",f"RED CARD! {mn}'\n{h} {hs}-{asc} {a}\n{sc}")}
      if t in mp:
       k,msg=mp[t]
       if not is_posted(k):
        if post_fb(msg+f"{HT}",make_hd([f"{t.upper()} {mn}'",f"{h} {hs}-{asc}",a,sc])):mark(k);cnt+=1
      if "var" in tl or "video review" in tl:
       k=f"var_{eid}_{did}"
       if not is_posted(k):
        if post_fb(f"VAR REVIEW! {mn}'\n{t}\n{h} {hs}-{asc} {a}\n{sc}{HT}",make_hd([f"VAR {mn}'",t[:30],f"{h} {hs}-{asc}"])):mark(k);cnt+=1
    is_ht=status.lower()=="halftime" or nstate.lower()=="status_halftime";is_ft=status.lower() in ["final","full time","ft"] or nstate.lower() in ["status_final","status_full_time"]
    if is_ht or is_ft:
     if not is_recent(ev.get("date","")):continue
     k=f"ht_{eid}" if is_ht else f"ft_{eid}_{hs}_{asc}";lb="HALFTIME" if is_ht else "FULL TIME"
     if is_posted(k) and (is_ht or is_posted(f"ft_photo_{eid}")):continue
     ft_goals=[]
     for d in details:
      if not isinstance(d,dict):continue
      t=d.get("type",{}).get("text","") if isinstance(d.get("type",{}),dict) else ""
      if t not in ["Goal","Own Goal","Penalty - Scored"]:continue
      inv=safe_list(d.get("athletesInvolved",[]));sc=inv[0].get("displayName","") if inv and isinstance(inv[0],dict) else "";mn=d.get("clock",{}).get("displayValue","") if isinstance(d.get("clock",{}),dict) else "";tid=d.get("team",{}).get("id","") if isinstance(d.get("team",{}),dict) else "";team_side="home" if tid==home.get("team",{}).get("id","") else "away";extra="(P)" if "Penalty" in t else "(OG)" if "Own" in t else "";ft_goals.append({"scorer":sc,"min":mn.replace("'",""),"extra":extra,"team":team_side})
     real_url=None
     if is_ft:
      win_sc=ft_goals[-1]["scorer"] if ft_goals else ""
      for fu in ["https://www.skysports.com/rss/12040","http://feeds.bbci.co.uk/sport/football/rss.xml","https://www.espn.com/espn/rss/soccer/news","https://www.goal.com/en/feeds/news","https://football-italia.net/feed/","https://www.theguardian.com/football/rss","https://www.90min.com/feeds/rss"]:
       try:
        feed=feedparser.parse(fu)
        for en in feed.entries[:40]:
         tlw=en.title.lower()
         if (h.lower().split()[-1] in tlw and a.lower().split()[-1] in tlw) or (win_sc and win_sc.lower().split()[0] in tlw):
          ru=get_img(en) or fetch_og(en.get("link",""))
          if ru:real_url=ru;break
        if real_url:break
       except:continue
     img=make_ft_final(h,a,hs,asc,ft_goals,real_url) if is_ft else make_hd([lb,f"{h} {hs}-{asc}",a])
     if not img:img=make_hd([lb,f"{h} {hs}-{asc} {a}"]+[f"{g['min']}' {g['scorer']}" for g in ft_goals[:3]])
     txt="\n"+" | ".join([f"{g['min']}' {g['scorer']}{g['extra']}" for g in ft_goals]) if ft_goals else ""
     if post_fb(f"{lb}\n{h} {hs}-{asc} {a}{txt}\n\nFollow UNFILTERED SCORES{HT}",img):mark(k);mark(f"ft_photo_{eid}") if real_url else None;cnt+=1
   except:continue
 return cnt
def process_news():
 try:
  for src,fu in [("BBC","http://feeds.bbci.co.uk/sport/football/rss.xml"),("Sky","https://www.skysports.com/rss/12040"),("Goal","https://www.goal.com/en/feeds/news")]:
   feed=feedparser.parse(fu)
   for en in feed.entries[:8]:
    t=en.get("title","")
    if not t or not is_fb(t):continue
    k=f"news_{t[:80]}"
    if is_posted(k):continue
    ri=get_img(en)
    if not ri:continue
    ib=make_real(ri)
    if not ib:continue
    if post_fb(f"{t}\n\nFollow UNFILTERED SCORES Source: {src}{HT}",ib):mark(k);return 1
 except:pass
 return 0
if __name__=="__main__":
 if len(FB_TOKEN)<50:exit(0)
 s=time.time()
 for i in range(25):
  try:process_live();process_news()
  except:pass
  if time.time()-s>550:break
  time.sleep(20)
