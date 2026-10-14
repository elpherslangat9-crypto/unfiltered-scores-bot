# V67 FINAL - FORCE POST WHEN 23 CANDIDATES FOUND
print("V67 FORCE POST LIVE - NO API KEY")
import os,json,requests
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image,ImageDraw,ImageFont

PID=os.getenv("PAGE_ID"); TOK=os.getenv("PAGE_ACCESS_TOKEN") or os.getenv("FB_TOKEN")
FILE="posted_state.json"; EAT=ZoneInfo("Africa/Nairobi")
BRAND_GREEN=(0,255,100)

def load():
 d={"goals":{},"kick":{},"ht":{},"ft":{}}
 try:
  with open(FILE) as f: s=json.load(f)
  for k in d: s.setdefault(k,d[k]); return s
 except: return d
def save(s): open(FILE,"w").write(json.dumps(s))

def mk(h,a,sc,lg,top):
 W,H=1080,1350; bg=Image.new("RGB",(W,H),(12,12,12))
 d=ImageDraw.Draw(bg)
 try: fb=ImageFont.truetype("DejaVuSans-Bold.ttf",75);fs=ImageFont.truetype("DejaVuSans-Bold.ttf",30)
 except: fb=fs=ImageFont.load_default()
 d.rounded_rectangle([30,20,W-30,85],radius=20,fill=BRAND_GREEN);d.text((50,30),f"{lg} {top}"[:44],font=fs,fill=(0,0,0))
 d.rounded_rectangle([280,700,800,830],radius=30,fill=(255,255,255));d.text((310,715),sc,font=fb,fill=(0,0,0))
 p="/tmp/m.png";bg.save(p,quality=95);return p

def post(msg,path):
 try:
  r=requests.post(f"https://graph.facebook.com/v20.0/{PID}/photos",data={"caption":msg,"access_token":TOK},files={"source":open(path,"rb")},timeout=30)
  print(f"FB {r.status_code} {r.text[:400]}"); return r.status_code==200
 except Exception as e: print(e); return False

def get_espn(lg):
 try:
  j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/scoreboard",timeout=8).json()
  evs=[]
  for e in j.get("events",[]):
   comp=e.get("competitions",[{}])[0]
   status=comp.get("status",{}).get("type",{}).get("name",""); short=comp.get("status",{}).get("type",{}).get("shortDetail","")
   comps=comp.get("competitors",[])
   try: h=next(c for c in comps if c["homeAway"]=="home"); a=next(c for c in comps if c["homeAway"]=="away")
   except:
    if len(comps)>=2: h=comps[0]; a=comps[1]
    else: continue
   print(f"ESPN {lg} {h['team']['displayName']} {h.get('score','0')}-{a.get('score','0')} {status} {short}")
   evs.append({"id":e.get("id"),"lg":lg,"h":h["team"]["displayName"],"a":a["team"]["displayName"],"hs":h.get("score","0"),"as":a.get("score","0"),"status":status,"short":short,"lname":{"ken.1":"KPL","uefa.champions":"UCL","eng.1":"Premier League"}.get(lg,lg)})
  return evs
 except Exception as ex: print(f"ESPN {lg} err {ex}"); return []

def main():
 st=load(); all_ev=[]
 for lg in ["ken.1","uefa.champions","eng.1"]:
  all_ev.extend(get_espn(lg))
 print(f"TOTAL CANDIDATES {len(all_ev)}")
 posted=0
 for ev in all_ev:
  # FORCE: post if status is IN_PROGRESS, HALFTIME, OR if shortDetail contains ' or HT or FT OR if it's UCL tonight
  is_live = ev["status"] in ["STATUS_IN_PROGRESS","STATUS_HALFTIME","STATUS_FINAL"] or "'" in ev["short"] or "HT" in ev["short"] or ev["short"].startswith("0-") is False and "PM" not in ev["short"]
  # Simpler: if scoreboard shows game today, and current time is after 9pm EAT, force live for UCL
  now_hour=datetime.now(EAT).hour
  if ev["lg"]=="uefa.champions" and now_hour>=21: is_live=True

  if not is_live: continue
  print(f"LIVE DETECTED {ev['h']} {ev['hs']}-{ev['as']} {ev['a']} {ev['short']}")
  key=f"{ev['id']}"
  score=f"{ev['hs']}-{ev['as']}"
  if key not in st["kick"]:
   img=mk(ev["h"],ev["a"],score,ev["lname"],ev["short"])
   if post(f"🔴 LIVE NOW {ev['lname']} {ev['h']} {score} {ev['a']} {ev['short']}\n\n#UCL #Live #ViralKE",img): st["kick"][key]=1; posted+=1
  # Goals
  gid=f"{key}_{score}"
  if score!="0-0" and gid not in st["goals"]:
   img=mk(ev["h"],ev["a"],score,ev["lname"],ev["short"])
   if post(f"GOAL! {ev['lname']} {ev['h']} {score} {ev['a']} {ev['short']}\n\n#Goal #Live",img): st["goals"][gid]=1; posted+=1

 # If still 0 posted but 23 candidates - post first 3 as TONIGHT LIVE
 if posted==0 and len(all_ev)>0:
  print("FORCE POSTING TONIGHT GAMES AS LIVE")
  for ev in all_ev[:3]:
   img=mk(ev["h"],ev["a"],f"{ev['hs']}-{ev['as']}",ev["lname"],ev["short"])
   if post(f"🔴 TONIGHT UCL {ev['h']} vs {ev['a']} {ev['short']}\n\nLive updates on page!\n\n#UCL #Live",img): posted+=1

 print(f"V67 DONE POSTED {posted}")
 save(st)

if __name__=="__main__": main()
