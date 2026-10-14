# V66 FINAL - NO API-FOOTBALL - ESPN + LIVESCORE + SOFASCORE FREE
print("V66 FREE ESPN+SOFASCORE+LIVESCORE - NO API KEY")
import os,json,requests,random
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image,ImageDraw,ImageFont

PID=os.getenv("PAGE_ID"); TOK=os.getenv("PAGE_ACCESS_TOKEN") or os.getenv("FB_TOKEN")
FILE="posted_state.json"; EAT=ZoneInfo("Africa/Nairobi")
BRAND_GREEN=(0,255,100)

def load():
 d={"goals":{},"kick":{},"ht":{},"ft":{},"today_posted":""}
 try:
  with open(FILE) as f: s=json.load(f)
  for k in d: s.setdefault(k,d[k]); return s
 except: return d
def save(s): open(FILE,"w").write(json.dumps(s))

def mk(h,a,sc,lg,top,bot):
 W,H=1080,1350; bg=Image.new("RGB",(W,H),(18,18,18))
 d=ImageDraw.Draw(bg)
 try: fb=ImageFont.truetype("DejaVuSans-Bold.ttf",80);fs=ImageFont.truetype("DejaVuSans-Bold.ttf",30);fs2=ImageFont.truetype("DejaVuSans-Bold.ttf",26)
 except: fb=fs=fs2=ImageFont.load_default()
 d.rounded_rectangle([30,20,W-30,85],radius=20,fill=BRAND_GREEN);d.text((50,30),f"{lg} {top}"[:42],font=fs,fill=(0,0,0))
 d.rounded_rectangle([280,700,800,830],radius=30,fill=(255,255,255));d.text((320,715),sc,font=fb,fill=(0,0,0))
 d.rounded_rectangle([30,1240,W-30,1320],radius=20,fill=BRAND_GREEN);d.text((40,1252),bot[:55],font=fs2,fill=(0,0,0))
 d.text((30,1150),f"{h} vs {a}"[:48],font=fs,fill=(255,255,255))
 p="/tmp/m.png";bg.save(p,quality=95);return p

def post(msg,path):
 try:
  r=requests.post(f"https://graph.facebook.com/v20.0/{PID}/photos",data={"caption":msg,"access_token":TOK},files={"source":open(path,"rb")},timeout=30)
  print(f"FB {r.status_code} {r.text[:500]}"); return r.status_code==200
 except Exception as e: print(f"FB ERR {e}"); return False

def get_espn(lg):
 try:
  j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/scoreboard",timeout=8).json()
  evs=[]
  for e in j.get("events",[]):
   comp=e.get("competitions",[{}])[0]
   status=comp.get("status",{}).get("type",{}).get("name","")
   short=comp.get("status",{}).get("type",{}).get("shortDetail","")
   comps=comp.get("competitors",[])
   try: h=next(c for c in comps if c["homeAway"]=="home"); a=next(c for c in comps if c["homeAway"]=="away")
   except: continue
   evs.append({"id":e.get("id"),"lg":lg,"h":h["team"]["displayName"],"a":a["team"]["displayName"],"hs":h.get("score","0"),"as":a.get("score","0"),"status":status,"short":short,"lname":{"ken.1":"KPL","uefa.champions":"UCL","eng.1":"Premier League"}.get(lg,lg)})
  return evs
 except Exception as ex: print(f"ESPN {lg} err {ex}"); return []

def get_sofa():
 # Try Sofa with different UA - if blocked, returns []
 evs=[]
 try:
  H={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64)","Referer":"https://www.sofascore.com/","Accept":"application/json"}
  r=requests.get("https://api.sofascore.com/api/v1/sport/football/events/live",timeout=8,headers=H)
  if r.status_code!=200:
   r=requests.get("https://api.sofascore.app/api/v1/sport/football/events/live",timeout=8,headers=H)
  j=r.json()
  for e in j.get("events",[]):
   tour=(e.get("tournament",{}).get("slug","")+e.get("tournament",{}).get("category",{}).get("slug","")).lower()
   if "champions" not in tour and "premier" not in tour and "kenya" not in tour and "uefa" not in tour: continue
   h=e.get("homeTeam",{}).get("name",""); a=e.get("awayTeam",{}).get("name","")
   hs=str(e.get("homeScore",{}).get("current",0)); as_=str(e.get("awayScore",{}).get("current",0))
   minute=e.get("time",{}).get("minute",0)
   st="STATUS_IN_PROGRESS" if minute>0 else "STATUS_SCHEDULED"
   evs.append({"id":f"sofa_{e.get('id')}","lg":"uefa.champions","h":h,"a":a,"hs":hs,"as":as_,"status":st,"short":f"{minute}'","lname":"UCL"})
  print(f"SOFASCORE LIVE {len(evs)}")
 except Exception as ex: print(f"Sofa blocked/err {ex}")
 return evs

def main():
 st=load(); all_ev=[]
 for lg in ["ken.1","uefa.champions","eng.1"]:
  all_ev.extend(get_espn(lg))
 all_ev.extend(get_sofa())
 print(f"TOTAL LIVE CANDIDATES {len(all_ev)}")
 posted=0
 for ev in all_ev:
  if ev["status"] not in ["STATUS_IN_PROGRESS","STATUS_HALFTIME"]: continue
  key=f"{ev['id']}"
  score=f"{ev['hs']}-{ev['as']}"
  tag="#UCL #ChampionsLeague #Viral" if ev["lname"]=="UCL" else "#KPL #FKFPL #ViralKE" if ev["lname"]=="KPL" else "#PremierLeague #EPL"
  if key not in st["kick"]:
   img=mk(ev["h"],ev["a"],score,ev["lname"],ev["short"],"KICK OFF - LIVE NOW")
   if post(f"🔴 LIVE NOW {ev['lname']} {ev['h']} {score} {ev['a']} ({ev['short']})\n\n{tag}",img): st["kick"][key]=1; posted+=1
  gid=f"{key}_{score}"
  if gid not in st["goals"]:
   # Skip 0-0 goal spam
   if score!="0-0" or ev["short"].lower() in ["ht","ft"]:
    img=mk(ev["h"],ev["a"],score,ev["lname"],ev["short"],"LIVE")
    if post(f"⚽ GOAL! {ev['lname']} {ev['h']} {score} {ev['a']} ({ev['short']})\n\n{tag}",img): st["goals"][gid]=1; posted+=1
  if ev["status"]=="STATUS_HALFTIME" and key not in st["ht"]:
   img=mk(ev["h"],ev["a"],score,ev["lname"],"HT","HALFTIME")
   if post(f"HALFTIME {ev['lname']} {ev['h']} {score} {ev['a']}\n\n{tag}",img): st["ht"][key]=1; posted+=1

 print(f"V66 DONE POSTED {posted}")
 save(st)

if __name__=="__main__": main()
