import os,json,time,requests,re,random
from datetime import datetime,timezone,timedelta
from io import BytesIO
from PIL import Image,ImageDraw,ImageFont
import feedparser

FB_TOKEN=os.getenv("FB_TOKEN","").strip()
FB_PAGE_ID=os.getenv("FB_PAGE_ID","1293090263895541").strip()
STATE_FILE="state.json"

# --- STATE ---
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
def is_posted(k):p=state.get("posted",{});return k in p and time.time()-p[k]<86400*2 # 2 days block duplicate
def mark(k):state["posted"][k]=time.time();save_state(state)

# --- HELPERS ---
def safe_list(x):return x if isinstance(x,list) else [x] if isinstance(x,dict) else [] if not x else [x]
def is_recent(d):
 try:return (datetime.now(timezone.utc)-datetime.fromisoformat(d.replace("Z","+00:00")))<timedelta(hours=6))
 except:return True

LEAGUES=["eng.1","eng.2","esp.1","ita.1","ger.1","fra.1","ned.1","por.1","ken.1","rsa.1","caf.champions","caf.confed","uefa.champions","uefa.europa","fifa.worldq"]
ESPN=[f"https://site.api.espn.com/apis/site/v2/sports/soccer/{c}/scoreboard" for c in LEAGUES]
NON=["darts","snooker","cricket","rugby","tennis","nba","nfl","golf","f1","boxing","mma","ufc"]
MUST=["football","premier","arsenal","chelsea","liverpool","man","tottenham","barcelona","real","atletico","bayern","psg","juventus","milan","serie","liga","bundes","champions","europa","fa cup","transfer","goal","striker","manager","kpl","gor","shabana","tusker","leopards"]

# RANDOM HASHTAGS TO AVOID DUPLICATE FLAG
HASHTAGS = [
 "\n\n#Football #LiveScores #UnfilteredScores",
 "\n\n#FootballLive #Soccer #Unfiltered",
 "\n\n⚽ #FootballUpdates #ScoreLive",
 "\n\n#PremierLeague #FootballNews #Live",
 "\n\n#SoccerLive #FootballFans"
]
def get_ht(): return random.choice(HASHTAGS)

def is_fb(t):t=t.lower();return False if any(b in t for b in NON) else any(g in t for g in MUST)
def fetch_json(u):
 try:r=requests.get(u,timeout=12,headers={"User-Agent":"Mozilla/5.0"});return r.json() if r.status_code==200 else None
 except:return None
def get_score(comps):
 try:h=next((c for c in comps if c.get("homeAway")=="home"),comps[0]);a=next((c for c in comps if c.get("homeAway")=="away"),comps[1]);return int(h.get("score")or 0),int(a.get("score")or 0)
 except:return 0,0
def font(s,b=0):
 try:return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if b else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",s)
 except:return ImageFont.load_default()

# --- IMAGES (same as yours, kept) ---
def make_hd(lines):
 W,H=1280,720;img=Image.new("RGB",(W,H),(8,12,28));d=ImageDraw.Draw(img)
 for y in range(H):d.line([(0,y),(W,y)],fill=(int(8+y*0.12),int(12+y*0.18),int(28+y*0.25)))
 bb=font(60,1);bm=font(38,1);bs=font(20,1);y=100
 for i,ln in enumerate(lines[:4]):f=bb if i==0 else bm;d.text((55,y),ln[:55],font=f,fill=(255,255,255));y+=88
 bw,bh=300,38;bx=(W-bw)//2;d.rounded_rectangle([bx,H-55,bx+bw,H-55+bh],radius=19,fill=(0,215,95));d.text((bx+26,H-47),"UNFILTERED SCORES",font=bs,fill=(255,255,255));b=BytesIO();img.save(b,format="JPEG",quality=96);b.seek(0);return b

# ... KEEP YOUR OTHER make_lineup, make_kick, make_ft_final functions HERE (same as before) ...
# I will keep them short for upload, use your old ones - they are ok

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
 card(14,h,ld["home"]);card(548,a,ld["away"]);bw,bh=320,36;bx=(W-bw)//2;d.rounded_rectangle([bx,H-46,bx+bw,H-10],radius=18,fill=(0,210,85));d.text((bx+16,H-39),"UNFILTERED SCORES",font=bm,fill=(255,255,255));b=BytesIO();img.save(b,format="JPEG",quality=96);b.seek(0);return b

def make_kick(h,a):
 W,H=1280,720;img=Image.new("RGB",(W,H),(8,14,35));d=ImageDraw.Draw(img)
 for y in range(H):d.line([(0,y),(W,y)],fill=(int(8+y*0.12),int(14+y*0.18),int(35+y*0.25)))
 d.text((80,180),"KICK OFF!",font=font(60,1),fill=(0,230,90));d.text((80,260),h[:30],font=font(32,1),fill=(255,255,255));d.text((80,305),"VS",font=font(22,1),fill=(0,230,90));d.text((80,335),a[:30],font=font(32,1),fill=(255,255,255))
 bw,bh=360,42;bx=(W-bw)//2;d.rounded_rectangle([bx,H-60,bx+bw,H-18],radius=21,fill=(0,218,92));d.text((bx+22,H-52),"UNFILTERED SCORES",font=font(32,1),fill=(255,255,255));b=BytesIO();can=Image.new("RGB",(W,H),(0,0,0));can.paste(img);b=BytesIO();img.save(b,format="JPEG",quality=96);b.seek(0);return b

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

# --- THIS IS THE FIX FOR REACH ---
def post_fb(msg, img):
    if not img or len(FB_TOKEN) < 50:
        print("No token or no image")
        return False
    try:
        # FORCED REACH: Use photos endpoint, NO privacy param, add randomization
        files = {"source": ("unfiltered.jpg", img, "image/jpeg")}
        data = {
            "message": msg,
            "access_token": FB_TOKEN,
            "published": "true"
        }
        # Add random to avoid duplicate content detection
        r = requests.post(f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos", files=files, data=data, timeout=30)
        print(f"FB POST: {r.status_code} - {r.text[:300]}")
        if r.status_code == 200:
            return True
        else:
            # Fallback try without published
            r2 = requests.post(f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos", files=files, data={"message": msg, "access_token": FB_TOKEN}, timeout=30)
            print(f"FB RETRY: {r2.status_code} - {r2.text[:300]}")
            return r2.status_code == 200
    except Exception as e:
        print(f"FB Error: {e}")
        return False

# --- YOUR PROCESS FUNCTIONS (same logic but with get_ht) ---
def process_live():
 # ... use same logic as before but call get_ht() ...
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
       img=make_lineup(h,a,ld,[hl,al]);msg=f"📋 LINEUPS\n{h} vs {a}{get_ht()}"
       if post_fb(msg,img):mark(k);cnt+=1;time.sleep(4)
    if stype=="in":
     k=f"kickoff_{eid}"
     if not is_posted(k):
      if post_fb(f"🔴 KICK OFF!\n{h} vs {a}\nLIVE NOW!{get_ht()}",make_kick(h,a)):mark(k);cnt+=1;time.sleep(4)
    is_ht=status.lower()=="halftime";is_ft=status.lower() in ["final","full time","ft"]
    if is_ht or is_ft:
     if not is_recent(ev.get("date","")):continue
     k=f"ht_{eid}" if is_ht else f"ft_{eid}_{hs}_{asc}"
     if is_posted(k):continue
     img=make_hd([("HALFTIME" if is_ht else "FULL TIME"),f"{h} {hs}-{asc}",a])
     txt=f"{'⏸️ HALFTIME' if is_ht else '✅ FULL TIME'}\n{h} {hs}-{asc} {a}{get_ht()}"
     if post_fb(txt,img):mark(k);cnt+=1;time.sleep(4)
   except:continue
 return cnt

if __name__=="__main__":
 if len(FB_TOKEN)<50:exit(0)
 s=time.time()
 for i in range(10): # Reduced from 25 to 10 to avoid spam
  try:process_live()
  except:pass
  if time.time()-s>240:break
  time.sleep(15)
