import os,json,time,requests,re
from datetime import datetime,timezone,timedelta
from io import BytesIO
from PIL import Image,ImageDraw,ImageFont
import feedparser
FB_TOKEN=os.getenv("FB_TOKEN","").strip();FB_PAGE_ID=os.getenv("FB_PAGE_ID","1293090263895541").strip();STATE_FILE="state.json"
def load_state():
 try:
  d=json.load(open(STATE_FILE))
  if isinstance(d.get("posted"),list):return {"posted":{k:time.time() for k in d["posted"]},"pred":d.get("pred",{})}
  return d
 except:return {"posted":{}, "pred":{}}
def save_state(s):
 try:json.dump(s,open(STATE_FILE,"w"))
 except:pass
state=load_state()
def is_posted(k):p=state.get("posted",{});return k in p and time.time()-p[k]<86400
def mark(k):state["posted"][k]=time.time();save_state(state)
def safe_list(x):return x if isinstance(x,list) else [x] if isinstance(x,dict) else [] if not x else [x]
def is_recent(d):
 try:return (datetime.now(timezone.utc)-datetime.fromisoformat(d.replace("Z","+00:00")))<timedelta(hours=5)
 except:return True
LEAGUES=["eng.1","eng.2","esp.1","ita.1","ger.1","fra.1","ned.1","por.1","ken.1","rsa.1","caf.champions","caf.confed","uefa.champions","uefa.europa","fifa.worldq"]
ESPN=[f"https://site.api.espn.com/apis/site/v2/sports/soccer/{c}/scoreboard" for c in LEAGUES]
NON=["darts","snooker","cricket","rugby","tennis","nba","nfl","golf","f1","boxing","mma","ufc"];MUST=["football","premier","arsenal","chelsea","liverpool","man","tottenham","barcelona","real","atletico","bayern","psg","juventus","milan","serie","liga","bundes","champions","europa","fa cup","transfer","goal","striker","manager","kpl","gor","shabana","tusker","leopards"];HT="\n\n#football #unfilteredscores"
def is_fb(t):t=t.lower();return False if any(b in t for b in NON) else any(g in t for g in MUST)
def fetch_json(u):
 try:r=requests.get(u,timeout=12,headers={"User-Agent":"Mozilla/5.0"});return r.json() if r.status_code==200 else None
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
    has=sum(1 for x in ap if x["s"]is not None);xi=[x for x in ap if x["s"]] if has else ap[:11];bn=[x for x in ap if not x["s"]] if has else ap[11:18];res[k]["xi"]=xi[:11];res[k]["bench"]=bn[:7]
   if len(res["home"]["xi"])>=7:return res
  except:continue
def make_lineup(h,a,ld,logos=None):
 W,H=1080,1150;img=Image.new("RGB",(W,H),(12,20,40));d=ImageDraw.Draw(img,"RGBA")
 for y in range(H):d.line([(0,y),(W,y)],fill=(int(12+y*0.04),int(20+y*0.07),int(42+y*0.1)))
 bb=font(32,1);bm=font(20,1);bs=font(16,1);bt=font(13);d.rounded_rectangle([12,10,W-12,92],radius=16,fill=(255,255,255,18))
 li=[]
 if logos:
  for u in logos:
   try:im=Image.open(BytesIO(requests.get(u,timeout=5).content)).convert("RGBA").resize((46,46),Image.LANCZOS);li.append(im)
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
# FIXED - WAS CAUSING SYNTAX ERROR
def fetch_og(u):
 try:
  t=requests.get(u,timeout=10,headers={"User-Agent":"Mozilla/5.0"}).text
  m=re.search(r'og:image.*?content="([^"]+)"',t,re.I)
  if not m:m=re.search(r"og:image.*?content='([^']+)'",t,re.I)
  if m:
   url=m.group(1)
   if url.startswith("//"):url="https:"+url
   return url.replace("/480/","/1280/")
 except:pass
 return None
def get_img(e):
 try:
  if hasattr(e,'media_content'):
   for mm in e.media_content:
    if mm.get('url'):return mm['url']
  if hasattr(e,'enclosures') and e.enclosures:return e.enclosures[0].get('href')
  if e.get("link"):return fetch_og(e.get("link"))
 except:pass
def make_real(url):
 try:r=requests.get(url,timeout=15).content;orig=Image.open(BytesIO(r)).convert("RGB");W,H=1280,720;can=Image.new("RGB",(W,H),(0,0,0));iw,ih=orig.size;ra=max(W/iw,H/ih);nw,nh=int(iw*ra),int(ih*ra);rs=orig.resize((nw,nh),Image.LANCZOS);can.paste(rs,((W-nw)//2,(H-nh)//2));d=ImageDraw.Draw(can,"RGBA");bw,bh=300,36;bx=(W-bw)//2;d.rounded_rectangle([bx,H-bh-12,bx+bw,H-12],radius=18,fill=(0,210,85,230));d.text((bx+20,H-29),"UNFILTERED SCORES",font=font(20,1),fill=(255,255,255));b=BytesIO();can.save(b,format="JPEG",quality=96);b.seek(0);return b
 except:return None
def make_ft_final(h,a,hs,asc,goals,real_url=None,logos=None):
 try:
  W,H=1080,1350;can=Image.new("RGB",(W,H),(10,18,42))
  if real_url:
   try:r=requests.get(real_url,timeout=12).content;orig=Image.open(BytesIO(r)).convert("RGB");iw,ih=orig.size;ra=max(W/iw,H/ih);nw,nh=int(iw*ra),int(ih*ra);rs=orig.resize((nw,nh),Image.LANCZOS);can.paste(rs,((W-nw)//2,(H-nh)//2))
   except:pass
  d=ImageDraw.Draw(can,"RGBA");cx,cy=30,H-380;cw,ch=W-60,340;d.rounded_rectangle([cx,cy,cx+cw,cy+ch],radius=22,fill=(18,18,20,175))
  bf=font(90,1);bs=font(17,1);bt=font(13,1);d.text((W//2,cy+14),"FULL TIME",font=bt,fill=(200,200,200),anchor="mm");d.text((W//2-58,cy+66),f"{hs}",font=bf,fill=(255,255,255),anchor="mm");d.text((W//2,cy+66),"-",font=bf,fill=(0,230,90),anchor="mm");d.text((W//2+58,cy+66),f"{asc}",font=bf,fill=(255,255,255),anchor="mm")
  y=cy+134
  for g in [x for x in goals if x["team"]=="home"][:5]:d.text((cx+16,y),f"{g['min']}' {g['scorer'][:18]} {g['extra']}",font=bs,fill=(255,255,255));y+=26
  y=cy+134
  for g in [x for x in goals if x["team"]=="away"][:5]:d.text((cx+cw-16,y),f"{g['scorer'][:18]} {g['extra']} {g['min']}'",font=bs,fill=(210,210,210),anchor="ra");y+=26
  bw,bh=240,26;bx=(W-bw)//2;by=H-34;d.rounded_rectangle([bx,by,bx+bw,by+bh],radius=13,fill=(0,210,85));d.text((bx+12,by+4),"UNFILTERED SCORES",font=bt,fill=(255,255,255));b=BytesIO();can.save(b,format="JPEG",quality=97);b.seek(0);return b
 except:return None
def make_pred_table(games,res=None):
 W,H=1280,900;img=Image.new("RGB",(W,H),(10,18,38));d=ImageDraw.Draw(img);fb=font(30,1);fm=font(19,1);fr=font(17,0);fs=font(15,1)
 d.rectangle([0,0,W,90],fill=(0,210,95));d.text((W//2,18),"DAILY 7 SURE GOALS - UNFILTERED SCORES",font=fb,fill=(255,255,255),anchor="mt");d.text((W//2,55),"Goals Only | 1.51+ | H2H & Form Analyzed",font=fs,fill=(255,255,255),anchor="mt")
 y=110;x=[30,80,480,780,950];d.rounded_rectangle([20,y,W-20,y+50],radius=12,fill=(25,35,65))
 for i,h in enumerate(["#","MATCH","PICK","ODDS","RESULT"]):d.text((x[i]+10 if i==0 else x[i],y+14),h,font=fm,fill=(0,210,95) if i==0 else (255,255,255))
 y+=65
 for idx,g in enumerate(games[:7]):
  ry=y+idx*85;fill=(18,28,55) if idx%2==0 else (22,35,68);d.rounded_rectangle([20,ry,W-20,ry+75],radius=10,fill=fill);d.ellipse([35,ry+20,70,ry+55],fill=(0,210,95));d.text((45,ry+25),str(idx+1),font=fs,fill=(255,255,255));d.text((x[1],ry+12),g['match'],font=fr,fill=(255,255,255));d.rounded_rectangle([x[2]-10,ry+15,x[2]+140,ry+50],radius=8,fill=(35,55,95));d.text((x[2],ry+20),g['pick'],font=fm,fill=(255,215,0));d.text((x[3],ry+25),f"@{g['odds']}",font=fm,fill=(255,255,255));r=res[idx] if res and idx<len(res) else "-";d.rounded_rectangle([x[4],ry+15,x[4]+110,ry+55],radius=8,fill=(0,210,95) if r=="✅" else (200,50,50) if r=="🚫" else (60,60,60));d.text((x[4]+35,ry+25),r,font=fm,fill=(255,255,255))
 fy=y+7*85+20;d.rounded_rectangle([20,fy,W-20,fy+55],radius=12,fill=(0,210,95));d.text((40,fy+15),"Total Odds: ~19.0 | UNFILTERED SCORES",font=fm,fill=(255,255,255));d.text((W-280,fy+15),"UNFILTERED SCORES",font=fm,fill=(255,255,255))
 b=BytesIO();img.save(b,format="JPEG",quality=95);b.seek(0);return b
def post_fb(msg,img):
 if not img or len(FB_TOKEN)<50:return False
 try:
  data={"message":msg,"access_token":FB_TOKEN,"published":"true","privacy":'{"value":"EVERYONE"}'}
  r=requests.post(f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos",files={"source":("hd.jpg",img,"image/jpeg")},data=data,timeout=30)
  return r.status_code==200
 except:return False
def process_live():
 today=datetime.now(timezone.utc).strftime("%Y-%m-%d");cnt=0;seen=set()
 for lu in ESPN:
  data=fetch_json(lu)
  if not data:continue
  for ev in data.get("events",[]):
   try:
    if not ev.get("date","").startswith(today):continue
    eid=ev.get("id","")
    if eid in seen:continue
    seen.add(eid)
    comp=ev.get("competitions",[{}])[0];status=comp.get("status",{}).get("type",{}).get("description","");stype=comp.get("status",{}).get("type",{}).get("state","");comps=comp.get("competitors",[])
    if len(comps)<2:continue
    home=next((c for c in comps if c.get("homeAway")=="home"),comps[0]);away=next((c for c in comps if c.get("homeAway")=="away"),comps[1]);h=home.get("team",{}).get("displayName","Home");a=away.get("team",{}).get("displayName","Away")
    hl=home.get("team",{}).get("logo","");al=away.get("team",{}).get("logo","");hs,asc=get_score(comps);details=safe_list(comp.get("details",[]))
    if stype=="pre":
     k=f"lineup_{eid}"
     if not is_posted(k):
      ld=fetch_lineups(eid)
      if ld:
       img=make_lineup(h,a,ld,[hl,al]);msg=f"LINEUPS\n{h} vs {a}\n{HT}"
       if post_fb(msg,img):mark(k);cnt+=1;time.sleep(3)
    if stype=="in":
     k=f"kickoff_{eid}"
     if not is_posted(k):
      if post_fb(f"KICK OFF!\n{h} vs {a}\nLIVE NOW!{HT}",make_kick(h,a)):mark(k);cnt+=1;time.sleep(3)
     for d in details:
      if not isinstance(d,dict):continue
      did=d.get("id","")
      if not did:continue
      t=d.get("type",{}).get("text","") if isinstance(d.get("type",{}),dict) else "";inv=safe_list(d.get("athletesInvolved",[]));sc=inv[0].get("displayName","") if inv and isinstance(inv[0],dict) else "";mn=d.get("clock",{}).get("displayValue","") if isinstance(d.get("clock",{}),dict) else "";tl=t.lower()
      mp={"Goal":(f"goal_{eid}_{did}",f"GOAL! {mn}'\n{h} {hs}-{asc} {a}\nScorer: {sc}"),"Own Goal":(f"owngoal_{eid}_{did}",f"OWN GOAL! {mn}'\n{h} {hs}-{asc} {a}\nBy {sc}"),"Penalty - Scored":(f"pen_{eid}_{did}",f"PENALTY! {mn}'\n{h} {hs}-{asc} {a}\nScorer: {sc}"),"Penalty - Missed":(f"penmiss_{eid}_{did}",f"PENALTY MISSED! {mn}'\n{h} {hs}-{asc} {a}\n{sc}"),"Red Card":(f"red_{eid}_{did}",f"RED CARD! {mn}'\n{h} {hs}-{asc} {a}\n{sc}"),"Yellow-Red Card":(f"red_{eid}_{did}",f"RED CARD! {mn}'\n{h} {hs}-{asc} {a}\n{sc}")}
      if t in mp:
       k,msg=mp[t]
       if not is_posted(k):
        if post_fb(msg+f"{HT}",make_hd([f"{t.upper()} {mn}'",f"{h} {hs}-{asc}",a,sc])):mark(k);cnt+=1;time.sleep(3)
      if "var" in tl or "video review" in tl:
       k=f"var_{eid}_{did}"
       if not is_posted(k):
        if post_fb(f"VAR REVIEW! {mn}'\n{t}\n{h} {hs}-{asc} {a}\n{sc}{HT}",make_hd([f"VAR {mn}'",t[:30],f"{h} {hs}-{asc}"])):mark(k);cnt+=1;time.sleep(3)
    is_ht=status.lower()=="halftime";is_ft=status.lower() in ["final","full time","ft"]
    if is_ht or is_ft:
     if not is_recent(ev.get("date","")):continue
     k=f"ht_{eid}" if is_ht else f"ft_{eid}_{hs}_{asc}"
     if is_posted(k):continue
     ft_goals=[]
     for d in details:
      if not isinstance(d,dict):continue
      t=d.get("type",{}).get("text","") if isinstance(d.get("type",{}),dict) else ""
      if t not in ["Goal","Own Goal","Penalty - Scored"]:continue
      inv=safe_list(d.get("athletesInvolved",[]));sc=inv[0].get("displayName","") if inv and isinstance(inv[0],dict) else "";mn=d.get("clock",{}).get("displayValue","") if isinstance(d.get("clock",{}),dict) else "";tid=d.get("team",{}).get("id","") if isinstance(d.get("team"),dict) else "";team_side="home" if tid==home.get("team",{}).get("id","") else "away";extra="(P)" if "Penalty" in t else "(OG)" if "Own" in t else "";ft_goals.append({"scorer":sc,"min":mn.replace("'",""),"extra":extra,"team":team_side})
     real_url=None
     if is_ft:
      win_sc=ft_goals[-1]["scorer"] if ft_goals else ""
      for fu in ["https://www.skysports.com/rss/12040","http://feeds.bbci.co.uk/sport/football/rss.xml","https://www.espn.com/espn/rss/soccer/news","https://www.goal.com/en/feeds/news","https://www.theguardian.com/football/rss","https://www.90min.com/feeds/rss","https://football-italia.net/feed/"]:
       try:
        feed=feedparser.parse(fu)
        for en in feed.entries[:40]:
         tlw=en.title.lower()
         if (h.lower().split()[-1] in tlw and a.lower().split()[-1] in tlw) or (win_sc and win_sc.lower().split()[0] in tlw):
          ru=get_img(en) or fetch_og(en.get("link",""))
          if ru:real_url=ru;break
        if real_url:break
       except:continue
     img=make_ft_final(h,a,hs,asc,ft_goals,real_url,[hl,al]) if is_ft else make_hd([("HALFTIME" if is_ht else "FULL TIME"),f"{h} {hs}-{asc}",a])
     if not img:img=make_hd([("HALFTIME" if is_ht else "FULL TIME"),f"{h} {hs}-{asc} {a}"])
     txt="\n"+" | ".join([f"{g['min']}' {g['scorer']}{g['extra']}" for g in ft_goals]) if ft_goals else ""
     if post_fb(f"{'HALFTIME' if is_ht else 'FULL TIME'}\n{h} {hs}-{asc} {a}{txt}\n\nFollow UNFILTERED SCORES{HT}",img):mark(k);cnt+=1;time.sleep(3)
   except:continue
 return cnt
def process_pred():
 today=datetime.now(timezone.utc).strftime("%Y-%m-%d")
 if datetime.now(timezone.utc).hour!=9:return 0
 k=f"pred_{today}"
 if is_posted(k):return 0
 games=[]
 for lu in ESPN:
  data=fetch_json(lu)
  if not data:continue
  for ev in data.get("events",[])[:20]:
   if not ev.get("date","").startswith(today):continue
   comp=ev.get("competitions",[{}])[0];comps=comp.get("competitors",[])
   if len(comps)<2:continue
   home=next((c for c in comps if c.get("homeAway")=="home"),comps[0]);away=next((c for c in comps if c.get("homeAway")=="away"),comps[1]);h=home.get("team",{}).get("displayName","Home");a=away.get("team",{}).get("displayName","Away")
   pick="Over 1.5";odds="1.55"
   if any(x in (h+a).lower() for x in ["city","barcelona","bayern","psg"]):pick="Over 2.5";odds="1.58"
   else:pick="BTTS Yes";odds="1.60"
   games.append({"match":f"{h[:18]} vs {a[:18]}","pick":pick,"odds":odds,"id":ev.get("id")})
   if len(games)>=7:break
  if len(games)>=7:break
 if len(games)<7:return 0
 img=make_pred_table(games);msg=f"🔥 DAILY 7 SURE GOALS - UNFILTERED SCORES 🔥\n"+"\n".join([f"{i+1}. {g['match']} - {g['pick']} @{g['odds']}" for i,g in enumerate(games)])+f"{HT}"
 if post_fb(msg,img):mark(k);state["pred"][today]=games;save_state(state);return 1
 return 0
def process_pred_res():
 today=datetime.now(timezone.utc).strftime("%Y-%m-%d")
 if datetime.now(timezone.utc).hour!=22:return 0
 k=f"pred_res_{today}"
 if is_posted(k):return 0
 pred=state.get("pred",{}).get(today)
 if not pred:return 0
 results=[];won=0
 for g in pred:
  for lu in ESPN:
   data=fetch_json(lu)
   if not data:continue
   for ev in data.get("events",[]):
    if ev.get("id")==g.get("id"):
     comp=ev.get("competitions",[{}])[0];hs,asc=get_score(comp.get("competitors",[]));ok=False
     if "1.5" in g["pick"] and hs+asc>=2:ok=True
     if "2.5" in g["pick"] and hs+asc>=3:ok=True
     if "BTTS" in g["pick"] and hs>=1 and asc>=1:ok=True
     results.append("✅" if ok else "🚫")
     if ok:won+=1
     break
 if len(results)<7:return 0
 img=make_pred_table(pred,results);booom="BOOOM ✅✅🟢 7/7!" if won==7 else f"{won}/7 Won";msg=f"{booom}\n"+"\n".join([f"{i+1}. {pred[i]['match']} {results[i]}" for i in range(7)])+f"{HT}"
 if post_fb(msg,img):mark(k);return 1
 return 0
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
  try:process_live();process_news();process_pred();process_pred_res()
  except:pass
  if time.time()-s>550:break
  time.sleep(20)
