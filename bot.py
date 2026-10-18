import os,json,time,requests,re
from datetime import datetime,timezone
from io import BytesIO
from PIL import Image,ImageDraw,ImageFont
import feedparser
FB_TOKEN=os.getenv("FB_TOKEN","").strip()
FB_PAGE_ID=os.getenv("FB_PAGE_ID","1293090263895541").strip()
STATE_FILE="state.json"
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
def fetch_lineups(eid):
 for lu in ESPN_LEAGUES:
  try:
   code=lu.split("/soccer/")[1].split("/scoreboard")[0]
   data=fetch_json(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/summary?event={eid}")
   if not data:continue
   rosters=data.get("rosters",[])
   if len(rosters)>=2:
    res={"home":{"xi":[],"bench":[]},"away":{"xi":[],"bench":[]}}
    for idx,ros in enumerate(rosters[:2]):
     key="home" if idx==0 else "away";xi=[];bench=[]
     for a in ros.get("roster",[]):
      if not isinstance(a,dict):continue
      ath=a.get("athlete",{});name=ath.get("displayName","") or a.get("displayName","")
      jer=str(a.get("jersey","") or "");pos=a.get("position",{}).get("abbreviation","")
      disp=f"{jer} {name} ({pos})".strip() if name else ""
      if a.get("starter"):xi.append(disp or name)
      else:bench.append(name)
     if not xi:
      xi=[r.get("athlete",{}).get("displayName","") for r in ros.get("roster",[])[:11]]
      bench=[r.get("athlete",{}).get("displayName","") for r in ros.get("roster",[])[11:18]]
     res[key]["xi"]=xi[:11];res[key]["bench"]=bench[:7]
    if res["home"]["xi"] and len(res["home"]["xi"])>=7:return res
  except:continue
 return None
def make_lineup(h,a,ld):
 W,H=1280,850
 img=Image.new("RGB",(W,H),(8,14,35))
 d=ImageDraw.Draw(img)
 for y in range(H):d.line([(0,y),(W,y)],fill=(int(8+y*0.1),int(14+y*0.15),int(35+y*0.22)))
 try:
  bb=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",32)
  bm=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",20)
  bs=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",17)
  bt=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",16)
 except:bb=bm=bs=bt=ImageFont.load_default()
 d.text((30,16),f"{h} vs {a}",font=bb,fill=(255,255,255))
 d.text((30,62),"★ LINEUPS + BENCH",font=bt,fill=(0,230,90))
 def card(x,team,dd):
  y0=98
  d.rounded_rectangle([x,y0-6,x+607,H-70],radius=14,fill=(255,255,255))
  d.rounded_rectangle([x,y0-6,x+607,y0+28],radius=14,fill=(0,200,85))
  d.rectangle([x,y0+14,x+607,y0+28],fill=(0,200,85))
  d.text((x+14,y0),team.upper()[:26],font=bm,fill=(255,255,255));y=y0+36
  for i,pl in enumerate(dd["xi"][:11]):
   d.ellipse([x+8,y-2,x+38,y+18],fill=(0,185,75))
   d.text((x+14,y),str(i+1),font=bs,fill=(255,255,255))
   d.text((x+46,y),pl[:28],font=bs,fill=(10,10,10));y+=34
  d.line([(x+8,y+2),(x+597,y+2)],fill=(0,200,85),width=2)
  d.text((x+12,y+6),"BENCH:",font=bt,fill=(0,150,60));y+=26
  for b in dd["bench"][:6]:d.text((x+12,y),f"• {b[:26]}",font=bt,fill=(30,30,30));y+=20
 card(18,h,ld["home"]);card(645,a,ld["away"])
 bw,bh=360,42;bx=(W-bw)//2;by=H-60
 d.rounded_rectangle([bx,by,bx+bw,by+bh],radius=21,fill=(0,218,92))
 d.text((bx+22,by+8),"🟢 UNFILTERED SCORES",font=bm,fill=(255,255,255))
 b=BytesIO();img.save(b,format="JPEG",quality=96);b.seek(0);return b
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
   for m in entry.media_content:
    if m.get('url'):return m['url']
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
def process_live():
 today=datetime.now(timezone.utc).strftime("%Y-%m-%d");cnt=0
 for lu in ESPN_LEAGUES:
  data=fetch_json(lu)
  if not data:continue
  for ev in data.get("events",[]):
   try:
    if ev.get("date","")[:10]!=today:continue
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
    details=safe_list(comp.get("details",[]));rh=0;ra=0;tl=[]
    for d in details:
     if not isinstance(d,dict):continue
     t=d.get("type",{}).get("text","") if isinstance(d.get("type",{}),dict) else ""
     if t in ["Goal","Own Goal","Penalty - Scored"]:
      tid=d.get("team",{}).get("id","") if isinstance(d.get("team",{}),dict) else ""
      is_h=tid==home.get("team",{}).get("id","")
      if is_h:rh+=1
      else:ra+=1
      inv=safe_list(d.get("athletesInvolved",[]));sc=inv[0].get("displayName","") if inv and isinstance(inv[0],dict) else ""
      mn=d.get("clock",{}).get("displayValue","") if isinstance(d.get("clock",{}),dict) else ""
      tl.append({"id":d.get("id",""),"minute":mn.replace("'",""),"h":rh,"a":ra,"scorer":sc,"type":t})
    if stype=="pre" or "SCHEDULED" in nstate:
     k=f"lineup_{eid}"
     if not is_posted(k):
      ld=fetch_lineups(eid)
      if ld:
       img=make_lineup(h,a,ld)
       msg=f"📋 LINEUPS + BENCH\n{h} vs {a}\n\n{h}: {', '.join([n.split('(')[0][:20] for n in ld['home']['xi'][:11]])}\nBench: {', '.join(ld['home']['bench'][:4])}\n\n{a}: {', '.join([n.split('(')[0][:20] for n in ld['away']['xi'][:11]])}\nBench: {', '.join(ld['away']['bench'][:4])}\n\nWho wins? 👇 Follow 🟢 UNFILTERED SCORES{HT}"
       if post_fb(msg,img):mark(k);cnt+=1
    if stype=="in" or "Half" in status or "In Progress" in status:
     k=f"kickoff_{eid}"
     if not is_posted(k):
      img=make_kick(h,a)
      msg=f"🔥 KICK OFF!\n{h} vs {a}\nLIVE NOW!\n\nPredict? 👇 Follow 🟢 UNFILTERED SCORES{HT}"
      if post_fb(msg,img):mark(k);cnt+=1
     for g in tl:
      k2=f"goal_{eid}_{g['id']}"
      if is_posted(k2) or stype=="post":continue
      if "Own Goal" in g['type']:msg=f"⚽ OWN GOAL! {g['minute']}'\n{h} {g['h']}-{g['a']} {a}\nBy {g['scorer']}\n\n🟢 UNFILTERED SCORES{HT}";img=make_hd([f"OWN GOAL {g['minute']}'",f"{h} {g['h']}-{g['a']}",a,g['scorer']])
      else:
       gt="PENALTY!" if "Penalty" in g['type'] else "GOAL!";msg=f"⚽ {gt} {g['minute']}'\n{h} {g['h']}-{g['a']} {a}\nScorer: {g['scorer']}\n\n🟢 UNFILTERED SCORES{HT}";img=make_hd([f"{gt} {g['minute']}'",f"{h} {g['h']}-{g['a']}",a,g['scorer']])
      if post_fb(msg,img):mark(k2);cnt+=1;time.sleep(1)
     for d in details:
      if not isinstance(d,dict):continue
      t=d.get("type",{}).get("text","") if isinstance(d.get("type",{}),dict) else ""
      if t in ["Red Card","Yellow-Red Card"]:
       k2=f"red_{eid}_{d.get('id','')}"
       if is_posted(k2) or stype=="post":continue
       inv=safe_list(d.get("athletesInvolved",[]));sc=inv[0].get("displayName","") if inv and isinstance(inv[0],dict) else "";mn=d.get("clock",{}).get("displayValue","") if isinstance(d.get("clock",{}),dict) else ""
       msg=f"🟥 RED CARD! {mn}'\n{h} {hs}-{asc} {a}\n{sc}\n\n🟢 UNFILTERED SCORES{HT}";img=make_hd([f"RED CARD {mn}'",f"{h} {hs}-{asc}",a,sc])
       if post_fb(msg,img):mark(k2);cnt+=1
    if "Half" in status or "Final" in status or "FT" in status or "FINAL" in nstate or "HALFTIME" in nstate:
     k=f"{status}_{eid}_{hs}_{asc}"
     if not is_posted(k):
      lb="⏸️ HALFTIME" if "Half" in status or "HALFTIME" in nstate else "✅ FULL TIME"
      is_ft="Final" in status or "FT" in status or "FINAL" in nstate;img=None
      if is_ft:
       try:
        feed=feedparser.parse("https://www.skysports.com/rss/12040")
        for entry in feed.entries[:15]:
         tlw=entry.title.lower()
         if h.split()[-1].lower() in tlw and a.split()[-1].lower() in tlw:
          ru=get_img(entry)
          if ru:img=make_real(ru);break
       except:pass
      if not img:img=make_hd([lb.replace("⏸️ ","").replace("✅ ",""),f"{h} {hs}-{asc}",a])
      msg=f"{lb}\n{h} {hs}-{asc} {a}\n\nFollow 🟢 UNFILTERED SCORES{HT}"
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
