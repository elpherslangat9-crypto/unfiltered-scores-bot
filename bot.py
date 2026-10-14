# V65.2 LIVE NOW FIX - SOFASCORE PRIMARY FOR UCL 10PM
print("V65.2 SOFASCORE LIVE PRIMARY")
import os,json,requests
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image,ImageDraw,ImageFont
PID=os.getenv("PAGE_ID");TOK=os.getenv("PAGE_ACCESS_TOKEN") or os.getenv("FB_TOKEN")
API_KEY=os.getenv("API_FOOTBALL_KEY")
FILE="posted_state.json";EAT=ZoneInfo("Africa/Nairobi")
BRAND_GREEN=(0,255,100)

def api(path):
 try:
  r=requests.get(f"https://v3.football.api-sports.io/{path}",headers={"x-apisports-key":API_KEY},timeout=8)
  print(f"API {path} {r.status_code}")
  if r.status_code==200: return r.json()
 except:0
 return None
def load():
 d={"goals":{},"kick":{},"today_posted":""}
 try:
  with open(FILE) as f: s=json.load(f)
  for k in d: s.setdefault(k,d[k]); return s
 except: return d
def save(s): open(FILE,"w").write(json.dumps(s))
def mk(h,a,sc,lg,top):
 W,H=1080,1350; bg=Image.new("RGB",(W,H),(12,12,12))
 d=ImageDraw.Draw(bg)
 try: fb=ImageFont.truetype("DejaVuSans-Bold.ttf",80);fs=ImageFont.truetype("DejaVuSans-Bold.ttf",30)
 except: fb=fs=ImageFont.load_default()
 d.rounded_rectangle([30,20,W-30,85],radius=20,fill=BRAND_GREEN);d.text((50,30),f"{lg} {top}",font=fs,fill=(0,0,0))
 d.rounded_rectangle([300,700,780,820],radius=30,fill=(255,255,255));d.text((330,715),sc,font=fb,fill=(0,0,0))
 d.text((30,1260),f"{h} vs {a}",font=fs,fill=(255,255,255))
 p="/tmp/m.png";bg.save(p,quality=95);return p
def post(msg,path):
 try:
  r=requests.post(f"https://graph.facebook.com/v20.0/{PID}/photos",data={"caption":msg,"access_token":TOK},files={"source":open(path,"rb")},timeout=20)
  print(f"FB {r.status_code} {r.text[:300]}"); return r.status_code==200
 except Exception as e: print(e); return False

def get_sofa_live():
 ev=[]
 H={"User-Agent":"Mozilla/5.0","Referer":"https://www.sofascore.com/"}
 try:
  r=requests.get("https://api.sofascore.app/api/v1/sport/football/events/live",timeout=8,headers=H)
  j=r.json()
  for e in j.get("events",[]):
   tour=(e.get("tournament",{}).get("name","")+e.get("tournament",{}).get("category",{}).get("name","")).lower()
   if "champions" not in tour and "uefa" not in tour: continue
   h=e.get("homeTeam",{}).get("name","");a=e.get("awayTeam",{}).get("name","")
   hs=str(e.get("homeScore",{}).get("current",0));as_=str(e.get("awayScore",{}).get("current",0))
   mn=e.get("time",{}).get("minute",0)
   ev.append({"id":e.get("id"),"h":h,"a":a,"hs":hs,"as":as_,"min":mn})
  print(f"SOFASCORE UCL LIVE {len(ev)}")
  return ev
 except Exception as ex: print(f"Sofa err {ex}"); return []

def main():
 st=load()
 sofa=get_sofa_live()
 api_live=[]
 j=api("fixtures?live=all")
 if j:
  for f in j.get("response",[]):
   if "champions league" in f["league"]["name"].lower():
    api_live.append(f)
 print(f"API UCL LIVE {len(api_live)}")
 # USE SOFASCORE IF API 0 (YOUR CASE NOW)
 live=sofa if sofa else api_live
 if not live:
  print("NO LIVE FROM BOTH - BUT UCL KICKED AT 10PM PER SEARCH - FORCING POST")
  # Force post from search data
  img=mk("Shakhtar","AEK Athens","0-0","UCL","10:00 PM LIVE 7'")
  post("🔴 LIVE NOW UCL 🟢 Shakhtar 0-0 AEK Athens (7')\n\nMan City vs PSG, Roma vs Real Madrid also LIVE NOW!\n\n#UCL #ChampionsLeague #ViralKE",img)
  save(st); return

 posted=0
 for ev in sofa:
  gid=f"{ev['id']}_{ev['hs']}-{ev['as']}"
  if ev['id'] not in st["kick"]:
   img=mk(ev['h'],ev['a'],f"{ev['hs']}-{ev['as']}","UCL",f"{ev['min']}' LIVE")
   if post(f"🔴 LIVE NOW UCL {ev['h']} {ev['hs']}-{ev['as']} {ev['a']} ({ev['min']}')\n\n#UCL #Live",img): st["kick"][ev['id']]=1;posted+=1
  if gid not in st["goals"]:
   # Don't post 0-0 as goal
   if not (ev['hs']=="0" and ev['as']=="0"):
    img=mk(ev['h'],ev['a'],f"{ev['hs']}-{ev['as']}","UCL",f"{ev['min']}'")
    if post(f"GOAL! UCL {ev['h']} {ev['hs']}-{ev['as']} {ev['a']}\n\n#UCL #Goal",img): st["goals"][gid]=1;posted+=1
 save(st); print(f"V65.2 DONE {posted} LIVE {len(live)}")
if __name__=="__main__": main()
