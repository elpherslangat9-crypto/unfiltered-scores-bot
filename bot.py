import os,json,time,requests,re
from datetime import datetime,timezone,timedelta
from io import BytesIO
from PIL import Image,ImageDraw,ImageFont
import feedparser
FB_TOKEN=os.getenv("FB_TOKEN","").strip()
FB_PAGE_ID=os.getenv("FB_PAGE_ID","1293090263895541").strip()
STATE_FILE="state.json"
RECENT_HOURS=3
def load_state():
 try:
  with open(STATE_FILE,"r") as f:return json.load(f)
 except:return {"posted":[]}
def save_state(s):
 try:
  with open(STATE_FILE,"w") as f:json.dump(s,f)
 except:pass
state=load_state()
def safe_list(x):
 if isinstance(x,list):return x
 if isinstance(x,dict):return [x]
 if not x:return []
 return [x]
def is_recent(d):
 try:
  dt=datetime.fromisoformat(d.replace("Z","+00:00"))
  return (datetime.now(timezone.utc)-dt) < timedelta(hours=RECENT_HOURS+2)
 except:return True
ESPN_LEAGUES=[
"https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard",
"https://site.api.espn.com/apis/site/v2/sports/soccer/eng.2/scoreboard",
"https://site.api.espn.com/apis/site/v2/sports/soccer/esp.1/scoreboard",
"https://site.api.espn.com/apis/site/v2/sports/soccer/ita.1/scoreboard",
"https://site.api.espn.com/apis/site/v2/sports/soccer/ger.1/scoreboard",
"https://site.api.espn.com/apis/site/v2/sports/soccer/fra.1/scoreboard",
"https://site.api.espn.com/apis/site/v2/sports/soccer/ned.1/scoreboard",
"https://site.api.espn.com/apis/site/v2/sports/soccer/por.1/scoreboard",
"https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/scoreboard",
"https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.europa/scoreboard",
"https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.worldq/scoreboard",
]
NON=["darts","van gerwen","snooker","cricket","rugby","tennis","nba","nfl","golf","f1","formula 1","boxing","mma","ufc","usyk","dubois","trilogy","fight","wrestling","athletics"]
MUST=["football","premier","arsenal","chelsea","liverpool","man utd","manchester city","man city","tottenham","barcelona","real madrid","atletico","bayern","dortmund","psg","juventus","ac milan","inter","serie a","la liga","bundesliga","ligue 1","efl","champions league","europa","fa cup","carabao","transfer","goal","striker","midfielder","defender","manager","coach","uefa","fifa","leeds","brentford","club","league","betis","como","fiorentina"]
HT="\n\n#football #premierleague #footballnews #unfilteredscores"
def is_fb(t):
 t=t.lower()
 for b in NON:
  if b in t:return False
 for g in MUST:
  if g in t:return True
 return False
def fetch_json(u):
 try:
  r=requests.get(u,timeout=15,headers={"User-Agent":"Mozilla/5.0"})
  if r.status_code==200:return r.json()
 except:pass
 return None
def get_score(comps):
 try:
  h=next((c for c in comps if c.get("homeAway")=="home"),comps[0])
  a=next((c for c in comps if c.get("homeAway")=="away"),comps[1])
  return int(h.get("score") or 0),int(a.get("score") or 0)
 except:return 0,0
def make_hd(lines):
 W,H=1280,720
 img=Image.new("RGB",(W,H),(8,12,28))
 d=ImageDraw.Draw(img)
 for y in range(H):d.line([(0,y),(W,y)],fill=(int(8+y*0.12),int(12+y*0.18),int(28+y*0.25)))
 try:
  bb=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",60)
  bm=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",38)
  bs=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",20)
 except:bb=bm=bs=ImageFont.load_default()
 y=100
 for i,ln in enumerate(lines[:4]):
  f=bb if i==0 else bm
  d.text((55,y),ln[:55],font=f,fill=(255,255,255));y+=88
  if i==0:d.line([(55,y-18),(320,y-18)],fill=(0,230,90),width=4)
 bw,bh=300,38;bx=(W-bw)//2;by=H-55
 d.rounded_rectangle([bx,by,bx+bw,by+bh],radius=19,fill=(0,215,95))
 d.text((bx+26,by+8),"🟢 UNFILTERED SCORES",font=bs,fill=(255,255,255))
 b=BytesIO();img.save(b,format="JPEG",quality=97);b.seek(0);return b

# FIXED - no SUB bug, needs both teams
def fetch_lineups(eid):
 for lu in ESPN_LEAGUES:
  try:
   code=lu.split("/soccer/")[1].split("/scoreboard")[0]
   data=fetch_json(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/summary?event={eid}")
   if not data:continue
   rosters=data.get("rosters",[])
   if len(rosters)<2:continue
   res={"home":{"xi":[],"bench":[]},"away":{"xi":[],"bench":[]}}
   for idx,ros in enumerate(rosters[:2]):
    key="home" if idx==0 else "away";all_p=[]
    for aa in ros.get("roster",[]):
     if not isinstance(aa,dict):continue
     ath=aa.get("athlete",{});name=ath.get("displayName","") or aa.get("displayName","")
     if not name:continue
     jer=str(aa.get("jersey","") or "");pos=aa.get("position",{}).get("abbreviation","")
     if pos=="SUB":pos=""
     all_p.append({"n":name,"j":jer,"p":pos,"s":aa.get("starter")})
    has=sum(1 for x in all_p if x["s"] is not None)
    if has>0:
     xi=[x for x in all_p if x["s"]];bn=[x for x in all_p if not x["s"]]
    else:xi=all_p[:11];bn=all_p[11:18]
    res[key]["xi"]=xi[:11];res[key]["bench"]=bn[:7]
   if len(res["home"]["xi"])>=7 and len(res["away"]["xi"])>=7:return res
  except:continue
 return None

# NEW - PREMIUM DECORATED LINEUP - SHORT + HD
def make_lineup(h,a,ld):
 W,H=1080,1350
 img=Image.new("RGB",(W,H),(12,20,40))
 d=ImageDraw.Draw(img,"RGBA")
 for y in range(H):d.line([(0,y),(W,y)],fill=(int(12+y*0.04),int(20+y*0.07),int(42+y*0.1)))
 try:
  bb=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",38)
  bm=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",22)
  bs=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",17)
  bt=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",14)
 except:bb=bm=bs=bt=ImageFont.load_default()
 d.rounded_rectangle([15,12,W-15,95],radius=16,fill=(255,255,255,12))
 d.text((22,18),f"{h} vs {a}",font=bb,fill=(255,255,255))
 d.text((22,68),"★ OFFICIAL LINEUPS",font=bt,fill=(0,230,120))
 def card(x,team,dd):
  y0=110;cw=515;ch=1075
  d.rounded_rectangle([x+3,y0+3,x+cw+3,y0+ch+3],radius=20,fill=(0,0,0,60))
  d.rounded_rectangle([x,y0,x+cw,y0+ch],radius=20,fill=(255,255,255))
  d.rounded_rectangle([x,y0,x+cw,y0+48],radius=20,fill=(0,200,88))
  d.rectangle([x,y0+24,x+cw,y0+48],fill=(0,200,88))
  d.text((x+14,y0+10),team.upper()[:20],font=bm,fill=(255,255,255))
  y=y0+56
  for i,p in enumerate(dd["xi"][:11]):
   d.ellipse([x+10,y,x+36,y+26],fill=(0,185,80))
   num=p.get("j","") or str(i+1)
   d.text((x+15 if len(num)==1 else x+12,y+3),num[:2],font=bs,fill=(255,255,255))
   d.text((x+46,y+2),p.get("n","")[:22],font=bs,fill=(15,15,15))
   y+=36
  d.line([(x+10,y+2),(x+cw-10,y+2)],fill=(0,200,88,90),width=2);y+=12
  d.text((x+12,y),"BENCH:",font=bt,fill=(0,150,60));y+=18
  for b in dd["bench"][:6]:
   txt=f"• {b.get('j','')} {b.get('n','')[:20]}" if isinstance(b,dict) else f"• {str(b)[:22]}"
   d.text((x+12,y),txt,font=bt,fill=(60,60,60));y+=18
 card(15,h,ld["home"]);card(550,a,ld["away"])
 bw,bh=340,40;bx=(W-bw)//2;by=H-52
 d.rounded_rectangle([bx,by,bx+bw,by+bh],radius=20,fill=(0,210,85))
 d.text((bx+18,by+8),"🟢 UNFILTERED SCORES",font=bm,fill=(255,255,255))
 b=BytesIO();img.save(b,format="JPEG",quality=97);b.seek(0);return b

def make_kick(h,a):
 W,H=1280,720
 img=Image.new("RGB",(W,H),(8,14,35))
 d=ImageDraw.Draw(img)
 for y in range(H):d.line([(0,y),(W,y)],fill=(int(8+y*0.12),int(14+y*0.18),int(35+y*0.25)))
 try:
  bb=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",60)
  bm=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",32)
  bs=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",22)
 except:bb=bm=bs=ImageFont.load_default()
 d.text((80,180),"⚽ KICK OFF!",font=bb,fill=(0,230,90))
 d.text((80,260),h[:30],font=bm,fill=(255,255,255))
 d.text((80,305),"VS",font=bs,fill=(0,230,90))
 d.text((80,335),a[:30],font=bm,fill=(255,255,255))
 d.text((80,395),"LIVE NOW - Predict? 👇",font=bs,fill=(255,255,100))
 bw,bh=360,42;bx=(W-bw)//2;by=H-60
 d.rounded_rectangle([bx,by,bx+bw,by+bh],radius=21,fill=(0,218,92))
 d.text((bx+22,by+8),"🟢 UNFILTERED SCORES",font=bm,fill=(255,255,255))
 b=BytesIO();img.save(b,format="JPEG",quality=96);b.seek(0);return b
def fetch_og(u):
 try:
  r=requests.get(u,timeout=15,headers={"User-Agent":"Mozilla/5.0 Chrome/120"})
  m=re.search(r'property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',r.text,re.I)
  if m:return m.group(1).replace("/480/","/1280/")
 except:pass
 return None
def get_img(entry):
 try:
  if hasattr(entry,'media_content'):
   for mm in entry.media_content:
    if mm.get('url'):return mm['url']
  if hasattr(entry,'enclosures') and entry.enclosures:
   href=entry.enclosures[0].get('href')
   if href and href.startswith("http"):return href
  link=entry.get("link","")
  if link:return fetch_og(link)
 except:pass
 return None
def make_real(url):
 try:
  r=requests.get(url,timeout=20,headers={"User-Agent":"Mozilla/5.0"})
  if r.status_code!=200:return None
  orig=Image.open(BytesIO(r.content)).convert("RGB")
  W,H=1280,720;can=Image.new("RGB",(W,H),(0,0,0))
  iw,ih=orig.size;ra=min(W/iw,H/ih);nw,nh=int(iw*ra),int(ih*ra)
  rs=orig.resize((nw,nh),Image.LANCZOS);x=(W-nw)//2;y=(H-nh)//2;can.paste(rs,(x,y))
  dr=ImageDraw.Draw(can,"RGBA")
  try:bs=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",20)
  except:bs=ImageFont.load_default()
  bw,bh=300,36;bx=(W-bw)//2;by=H-bh-12
  dr.rounded_rectangle([bx,by,bx+bw,by+bh],radius=18,fill=(0,210,85,230))
  dr.text((bx+20,by+7),"🟢 UNFILTERED SCORES",font=bs,fill=(255,255,255))
  b=BytesIO();can.save(b,format="JPEG",quality=96);b.seek(0);return b
 except:return None
def make_ft_final(h,a,hs,asc,goals,real_url=None):
 try:
  W,H=1080,1350
  can=Image.new("RGB",(W,H),(12,12,16))
  d=ImageDraw.Draw(can)
  top_h=840
  if real_url:
   try:
    r=requests.get(real_url,timeout=20,headers={"User-Agent":"Mozilla/5.0"})
    if r.status_code==200:
     orig=Image.open(BytesIO(r.content)).convert("RGB")
     iw,ih=orig.size;ra=max(W/iw,top_h/ih);nw,nh=int(iw*ra),int(ih*ra)
     rs=orig.resize((nw,nh),Image.LANCZOS);x=(W-nw)//2;can.paste(rs,(x,0))
   except:pass
  d.rectangle([0,top_h,W,H],fill=(0,0,0))
  d.line([(20,top_h+6),(W-20,top_h+6)],fill=(0,230,90),width=3)
  try:
   bf=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",78)
   bm=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",24)
   bs=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",20)
   bb=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",18)
  except:bf=bm=bs=bb=ImageFont.load_default()
  d.text((30,top_h+18),h[:20].upper(),font=bm,fill=(255,255,255))
  d.text((W-240,top_h+18),a[:20].upper(),font=bm,fill=(255,255,255))
  d.text((W//2-85,top_h+8),f"{hs} - {asc}",font=bf,fill=(255,255,255))
  d.text((W//2-18,top_h+92),"FT",font=bb,fill=(0,230,90))
  hg=[g for g in goals if g["team"]=="home"];ag=[g for g in goals if g["team"]=="away"]
  y1=top_h+120
  for g in hg[:5]:
   d.text((28,y1),f"{g['min']}' | {g['scorer'][:18]} {g['extra']}",font=bs,fill=(230,230,230));y1+=26
  y2=top_h+120
  for g in ag[:5]:
   d.text((W//2+18,y2),f"{g['scorer'][:18]} {g['extra']} | {g['min']}'",font=bs,fill=(210,210,210));y2+=26
  bw,bh=310,34;bx=(W-bw)//2;by=H-42
  d.rounded_rectangle([bx,by,bx+bw,by+bh],radius=17,fill=(0,210,85))
  d.text((bx+16,by+6),"🟢 UNFILTERED SCORES",font=bs,fill=(255,255,255))
  b=BytesIO();can.save(b,format="JPEG",quality=96);b.seek(0);return b
 except:return None
def post_fb(msg,img):
 if len(FB_TOKEN)<50:return False
 try:
  url=f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
  files={"source":("hd.jpg",img,"image/jpeg")}
  data={"message":msg,"access_token":FB_TOKEN}
  r=requests.post(url,files=files,data=data,timeout=35)
  return r.status_code==200
 except:return False
def is_posted(k):return k in state.get("posted",[])
def mark(k):
 p=state.get("posted",[]);p.append(k);state["posted"]=p[-1000:];save_state(state)
def get_winning_scorer(ft_goals,hs,asc,h,a):
 try:
  if not ft_goals:return None
  win="home" if hs>asc else "away" if asc>hs else "home"
  winners=[g for g in ft_goals if g["team"]==win]
  if winners:return winners[-1]["scorer"]
  return ft_goals[-1]["scorer"]
 except:return None
def process_live():
 today=datetime.now(timezone.utc).strftime("%Y-%m-%d");cnt=0
 for lu in ESPN_LEAGUES:
  data=fetch_json(lu)
  if not data:continue
  for ev in data.get("events",[]):
   try:
    ev_date=ev.get("date","")
    if not ev_date or ev_date[:10]!=today:continue
    comp=ev.get("competitions",[{}])[0]
    status=comp.get("status",{}).get("type",{}).get("description","")
    stype=comp.get("status",{}).get("type",{}).get("state","")
    nstate=comp.get("status",{}).get("type",{}).get("name","")
    comps=comp.get("competitors",[])
    if len(comps)<2:continue
    home=next((c for c in comps if c.get("homeAway")=="home"),comps[0])
    away=next((c for c in comps if c.get("homeAway")=="away"),comps[1])
    h=home.get("team",{}).get("displayName","Home");a=away.get("team",{}).get("displayName","Away")
    eid=ev.get("id","");hs,asc=get_score(comps)
    details=safe_list(comp.get("details",[]))
    if stype=="pre" or "SCHEDULED" in nstate:
     k=f"lineup_{eid}"
     if not is_posted(k):
      ld=fetch_lineups(eid)
      if ld:
       img=make_lineup(h,a,ld)
       def fmt(p):return p.get("n","")[:20] if isinstance(p,dict) else str(p)[:20]
       msg=f"📋 LINEUPS + BENCH\n{h} vs {a}\n\n{h}: {', '.join([fmt(n) for n in ld['home']['xi'][:11]])}\nBench: {', '.join([fmt(n) for n in ld['home']['bench'][:4]])}\n\n{a}: {', '.join([fmt(n) for n in ld['away']['xi'][:11]])}\nBench: {', '.join([fmt(n) for n in ld['away']['bench'][:4]])}\n\nWho wins? 👇 Follow 🟢 UNFILTERED SCORES{HT}"
       if post_fb(msg,img):mark(k);cnt+=1
    if stype=="in":
     k=f"kickoff_{eid}"
     if not is_posted(k):
      img=make_kick(h,a)
      msg=f"🔥 KICK OFF!\n{h} vs {a}\nLIVE NOW!\n\nPredict? 👇 Follow 🟢 UNFILTERED SCORES{HT}"
      if post_fb(msg,img):mark(k);cnt+=1
    if stype=="in":
     for d in details:
      if not isinstance(d,dict):continue
      did=d.get("id","")
      if not did:continue
      t=d.get("type",{}).get("text","") if isinstance(d.get("type",{}),dict) else ""
      if not t:continue
      inv=safe_list(d.get("athletesInvolved",[]))
      sc=inv[0].get("displayName","") if inv and isinstance(inv[0],dict) else ""
      mn=d.get("clock",{}).get("displayValue","") if isinstance(d.get("clock",{}),dict) else ""
      t_low=t.lower()
      if t=="Goal":
       k=f"goal_{eid}_{did}"
       if is_posted(k):continue
       msg=f"⚽ GOAL! {mn}'\n{h} {hs}-{asc} {a}\nScorer: {sc}\n\n🟢 UNFILTERED SCORES{HT}"
       img=make_hd([f"GOAL {mn}'",f"{h} {hs}-{asc}",a,sc])
       if post_fb(msg,img):mark(k);cnt+=1;time.sleep(1)
      elif t=="Own Goal":
       k=f"owngoal_{eid}_{did}"
       if is_posted(k):continue
       msg=f"⚽ OWN GOAL! {mn}'\n{h} {hs}-{asc} {a}\nBy {sc}\n\n🟢 UNFILTERED SCORES{HT}"
       img=make_hd([f"OWN GOAL {mn}'",f"{h} {hs}-{asc}",a,sc])
       if post_fb(msg,img):mark(k);cnt+=1;time.sleep(1)
      elif t=="Penalty - Scored":
       k=f"pen_{eid}_{did}"
       if is_posted(k):continue
       msg=f"⚽ PENALTY! {mn}'\n{h} {hs}-{asc} {a}\nScorer: {sc}\n\n🟢 UNFILTERED SCORES{HT}"
       img=make_hd([f"PENALTY {mn}'",f"{h} {hs}-{asc}",a,sc])
       if post_fb(msg,img):mark(k);cnt+=1;time.sleep(1)
      elif t=="Penalty - Missed":
       k=f"penmiss_{eid}_{did}"
       if is_posted(k):continue
       msg=f"❌ PENALTY MISSED! {mn}'\n{h} {hs}-{asc} {a}\nMissed: {sc}\n\n🟢 UNFILTERED SCORES{HT}"
       img=make_hd([f"PEN MISS {mn}'",f"{h} {hs}-{asc}",a,sc])
       if post_fb(msg,img):mark(k);cnt+=1
      elif t in ["Red Card","Yellow-Red Card"]:
       k=f"red_{eid}_{did}"
       if is_posted(k):continue
       msg=f"🟥 RED CARD! {mn}'\n{h} {hs}-{asc} {a}\n{sc}\n\n🟢 UNFILTERED SCORES{HT}"
       img=make_hd([f"RED CARD {mn}'",f"{h} {hs}-{asc}",a,sc])
       if post_fb(msg,img):mark(k);cnt+=1
      elif "var" in t_low or "video review" in t_low:
       k=f"var_{eid}_{did}"
       if is_posted(k):continue
       msg=f"📺 VAR REVIEW! {mn}'\n{t}\n{h} {hs}-{asc} {a}\n{sc}\n\n🟢 UNFILTERED SCORES{HT}"
       img=make_hd([f"VAR {mn}'",t[:30],f"{h} {hs}-{asc}"])
       if post_fb(msg,img):mark(k);cnt+=1
    s_low=status.lower();n_low=nstate.lower()
    is_ht=s_low=="halftime" or n_low=="status_halftime"
    is_ft=s_low in ["final","full time","ft"] or n_low in ["status_final","status_full_time"]
    if is_ht or is_ft:
     if not is_recent(ev_date):continue
     k=f"ht_{eid}" if is_ht else f"ft_{eid}_{hs}_{asc}"
     lb="⏸️ HALFTIME" if is_ht else "✅ FULL TIME"
     if not is_posted(k):
      ft_goals=[]
      for d in details:
       if not isinstance(d,dict):continue
       t=d.get("type",{}).get("text","") if isinstance(d.get("type",{}),dict) else ""
       if t not in ["Goal","Own Goal","Penalty - Scored"]:continue
       inv=safe_list(d.get("athletesInvolved",[]))
       sc=inv[0].get("displayName","") if inv and isinstance(inv[0],dict) else ""
       mn=d.get("clock",{}).get("displayValue","") if isinstance(d.get("clock",{}),dict) else ""
       tid=d.get("team",{}).get("id","") if isinstance(d.get("team",{}),dict) else ""
       team_side="home" if tid==home.get("team",{}).get("id","") else "away"
       extra="(P)" if "Penalty" in t else "(OG)" if "Own" in t else ""
       ft_goals.append({"scorer":sc,"min":mn.replace("'",""),"extra":extra,"team":team_side})
      real_url=None;win_scorer=get_winning_scorer(ft_goals,hs,asc,h,a)
      if is_ft:
       for feed_url in ["https://www.skysports.com/rss/12040","http://feeds.bbci.co.uk/sport/football/rss.xml"]:
        try:
         feed=feedparser.parse(feed_url)
         for entry in feed.entries[:25]:
          tlw=entry.title.lower()
          hw=h.lower().split()[-1];aw=a.lower().split()[-1]
          if (hw in tlw and aw in tlw) or (win_scorer and win_scorer.lower().split()[0] in tlw):
           ru=get_img(entry)
           if ru:real_url=ru;break
         if real_url:break
        except:continue
      img=make_ft_final(h,a,hs,asc,ft_goals,real_url) if is_ft else None
      if not img:
       if is_ht:img=make_hd([lb.replace("⏸️ ",""),f"{h} {hs}-{asc}",a])
       else:
        lines=[lb.replace("✅ ",""),f"{h} {hs}-{asc} {a}"]
        for g in ft_goals[:4]:lines.append(f"{g['min']}' {g['scorer']} {g['extra']}")
        img=make_hd(lines)
      scorers_txt="\n"+" | ".join([f"{g['min']}' {g['scorer']}{g['extra']}" for g in ft_goals]) if ft_goals else ""
      msg=f"{lb}\n{h} {hs}-{asc} {a}{scorers_txt}\n\nFollow 🟢 UNFILTERED SCORES{HT}"
      if post_fb(msg,img):mark(k);cnt+=1
   except:continue
 return cnt
def process_news():
 try:
  feeds=[("BBC","http://feeds.bbci.co.uk/sport/football/rss.xml"),("Sky","https://www.skysports.com/rss/12040")]
  for src,fu in feeds:
   feed=feedparser.parse(fu)
   for entry in feed.entries[:10]:
    title=entry.get("title","")
    if not title or not is_fb(title):continue
    k=f"news_{title[:80]}"
    if is_posted(k):continue
    ri=get_img(entry)
    if not ri:continue
    ib=make_real(ri)
    if not ib:continue
    msg=f"🚨 {title}\n\nFollow 🟢 UNFILTERED SCORES ⚽\nSource: {src}{HT}"
    if post_fb(msg,ib):mark(k);return 1
 except:pass
 return 0
if __name__=="__main__":
 if len(FB_TOKEN)<50:exit(0)
 start=time.time()
 for i in range(25):
  try:
   process_live()
   if i%2==0:process_news()
  except:pass
  if time.time()-start>550:break
  time.sleep(20)
