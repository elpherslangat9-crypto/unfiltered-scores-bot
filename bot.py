# V65 FINAL - UNRESTRICTED + TODAY FIXTURES + LIVE + NEWS
print("V65 UNRESTRICTED + TODAY FIXTURES + NEWS")
import os,json,requests,random,time
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image,ImageDraw,ImageFont
from io import BytesIO

PID=os.getenv("PAGE_ID");TOK=os.getenv("PAGE_ACCESS_TOKEN") or os.getenv("FB_TOKEN")
API_KEY=os.getenv("API_FOOTBALL_KEY")
FILE="posted_state.json";EAT=ZoneInfo("Africa/Nairobi")
BRAND_GREEN=(0,255,100)

def api(path):
 if not API_KEY: return None
 try:
  r=requests.get(f"https://v3.football.api-sports.io/{path}",headers={"x-apisports-key":API_KEY},timeout=10)
  print(f"API CALL {path} STATUS {r.status_code}")
  if r.status_code==200: return r.json()
  print(r.text[:500])
 except Exception as e: print(f"API ERR {e}")
 return None

def load():
 d={"goals":{},"ht":{},"ft":{},"last":{},"kick":{},"news":[],"today_posted":"","last_news_time":0}
 try:
  with open(FILE) as f: s=json.load(f)
  for k in d: s.setdefault(k,d[k]); return s
 except: return d
def save(s): open(FILE,"w").write(json.dumps(s))

def dl(u):
 try:
  r=requests.get(u,timeout=10,headers={"User-Agent":"Mozilla/5.0"})
  if r.status_code==200 and len(r.content)>3000: return Image.open(BytesIO(r.content)).convert("RGBA")
 except:0
 return None

def mk(h,a,sc,lg,top,bot,g):
 W,H=1080,1350
 bg=g.convert("RGB").resize((W,H),Image.LANCZOS) if g else Image.new("RGB",(W,H),(12,12,12))
 if g: bg=Image.blend(bg,Image.new("RGB",(W,H),(0,0,0)),0.45)
 d=ImageDraw.Draw(bg)
 try: fb=ImageFont.truetype("DejaVuSans-Bold.ttf",70);fs=ImageFont.truetype("DejaVuSans-Bold.ttf",32);fs2=ImageFont.truetype("DejaVuSans-Bold.ttf",26)
 except: fb=fs=fs2=ImageFont.load_default()
 d.rounded_rectangle([30,20,W-30,85],radius=20,fill=BRAND_GREEN);d.text((50,30),f"Unfiltered {lg} {top}"[:44],font=fs,fill=(0,0,0))
 d.rounded_rectangle([260,680,820,820],radius=30,fill=(255,255,255));d.text((290,700),sc,font=fb,fill=(0,0,0))
 d.rounded_rectangle([30,1240,W-30,1320],radius=20,fill=BRAND_GREEN);d.text((40,1252),bot[:56],font=fs2,fill=(0,0,0))
 p="/tmp/m.png";bg.save(p,quality=95);return p

def post(msg,path):
 try:
  r=requests.post(f"https://graph.facebook.com/v20.0/{PID}/photos",data={"caption":msg,"access_token":TOK},files={"source":open(path,"rb")},timeout=30)
  print(f"FB {r.status_code} {r.text[:400]}"); return r.status_code==200
 except Exception as e: print(f"FB ERR {e}"); return False

def run_once(st):
 today=datetime.now(EAT).strftime("%Y-%m-%d")
 # 1. LIVE NOW
 live_events=[]
 j=api("fixtures?live=all")
 if j:
  for f in j.get("response",[]):
   try:
    ln=f["league"]["name"].lower()
    if "kenya" in ln: lname="KPL";code="ken.1"
    elif "champions league" in ln: lname="UCL";code="uefa.champions"
    elif "premier league" in ln: lname="Premier League";code="eng.1"
    else: continue
    h=f["teams"]["home"]["name"];a=f["teams"]["away"]["name"]
    hs=str(f["goals"]["home"] or 0);ass=str(f["goals"]["away"] or 0)
    stt=f["fixture"]["status"]["short"];m={"1H":"STATUS_IN_PROGRESS","2H":"STATUS_IN_PROGRESS","HT":"STATUS_HALFTIME","FT":"STATUS_FINAL"}
    live_events.append({"id":f['fixture']['id'],"lname":lname,"h":h,"a":a,"hs":hs,"as":ass,"status":m.get(stt,"OTHER"),"short":stt,"time":f["fixture"]["date"]})
   except:0
 print(f"API LIVE {len(live_events)}")
 posted=0
 # POST LIVE
 for ev in live_events:
  gid=f"{ev['id']}_{ev['hs']}-{ev['as']}"
  ground=dl(f"https://picsum.photos/seed/{ev['h'][:3]}{ev['a'][:3]}/1080/1350")
  tag="#KPL #FKFPL #ViralKE" if ev['lname']=="KPL" else "#UCL #ChampionsLeague"
  if ev['status'] in ["STATUS_IN_PROGRESS","STATUS_HALFTIME"]:
   if ev['id'] not in st["kick"]:
    img=mk(ev['h'],ev['a'],f"{ev['hs']}-{ev['as']}",ev['lname'],ev['short'],"KICK OFF LIVE",ground)
    if post(f"🔴 LIVE NOW {ev['lname']} {ev['h']} {ev['hs']}-{ev['as']} {ev['a']}\n\n{tag}",img): st["kick"][ev['id']]=1;posted+=1
   if gid not in st["goals"]:
    img=mk(ev['h'],ev['a'],f"{ev['hs']}-{ev['as']}",ev['lname'],ev['short'],"Live",ground)
    if post(f"GOAL! {ev['lname']} {ev['h']} {ev['hs']}-{ev['as']} {ev['a']}\n\n{tag}",img): st["goals"][gid]=1;posted+=1

 # 2. IF NO LIVE - POST TODAY'S FIXTURES
 if len(live_events)==0:
  print("NO LIVE - CHECKING TODAY FIXTURES")
  if st.get("today_posted")!=today:
   jf=api(f"fixtures?date={today}")
   if jf:
    todays=[]
    for f in jf.get("response",[]):
     try:
      ln=f["league"]["name"].lower()
      if "kenya" in ln: lname="KPL"
      elif "champions league" in ln: lname="UCL"
      elif "premier league" in ln and "england" in ln: lname="Premier League"
      else: continue
      h=f["teams"]["home"]["name"];a=f["teams"]["away"]["name"]
      dt=datetime.fromisoformat(f["fixture"]["date"].replace("Z","+00:00")).astimezone(EAT)
      todays.append(f"{lname}: {h} vs {a} at {dt.strftime('%I:%M %p')} EAT")
     except:0
    if todays:
     # Create one image with today's fixtures
     W,H=1080,1350; bg=Image.new("RGB",(W,H),(12,12,12)); d=ImageDraw.Draw(bg)
     try: fs=ImageFont.truetype("DejaVuSans-Bold.ttf",32);fb=ImageFont.truetype("DejaVuSans-Bold.ttf",48)
     except: fs=fb=ImageFont.load_default()
     d.rounded_rectangle([30,20,W-30,85],radius=20,fill=BRAND_GREEN);d.text((50,30),f"TODAY {today} FIXTURES",font=fs,fill=(0,0,0))
     y=120
     for t in todays[:10]:
      d.text((40,y),t[:58],font=fs,fill=(255,255,255)); y+=90
     p="/tmp/m.png";bg.save(p,quality=95)
     msg="🟢 TODAY'S FIXTURES 🟢\n\n"+"\n".join(todays[:10])+"\n\n#KPL #UCL #PremierLeague #ViralKE"
     if post(msg,p): st["today_posted"]=today; posted+=1
     print(f"TODAY POSTED {len(todays)}")
    else: print("NO FIXTURES TODAY IN API")
  else: print(f"TODAY {today} ALREADY POSTED")
 else: print(f"LIVE {len(live_events)} - SKIP TODAY FIXTURES")

 return posted

def main():
 st=load(); tot=run_once(st); save(st); print(f"V65 DONE {tot}")
if __name__=="__main__": main()
