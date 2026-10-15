# V75 BRAND GREEN - FORCE 1 POST TO PROVE FB WORKS - DEBUG WHY 0/5
print("V75 BRAND GREEN FORCE TEST LOADED")
import os,json,requests,re,time
from PIL import Image,ImageDraw,ImageFont
from concurrent.futures import ThreadPoolExecutor

PID=os.getenv("PAGE_ID");TOK=os.getenv("PAGE_ACCESS_TOKEN") or os.getenv("FB_TOKEN")
FILE="posted_state.json"
NAMES={"eng.1":"Premier League","esp.1":"LaLiga","ger.1":"Bundesliga","ita.1":"Serie A","fra.1":"Ligue 1","ken.1":"KPL","usa.1":"MLS","uefa.champions":"UCL","uefa.europa":"Europa","eng.2":"Championship"}
PR=list(NAMES.keys())

def load():
 # FORCE RESET IF FILE TOO BIG = STUCK
 try:
  d=json.load(open(FILE))
  if len(d.get("kick",{})) > 200: # too many, reset
   print("RESETTING STUCK STATE")
   raise Exception("reset")
  return {"last":d.get("last",{}),"goals":d.get("goals",{}),"ht":d.get("ht",{}),"ft":d.get("ft",{}),"red":d.get("red",{}),"kick":d.get("kick",{}),"news":[]}
 except:
  print("FRESH STATE CREATED")
  return {"last":{},"goals":{},"ht":{},"ft":{},"red":{},"kick":{},"news":[]}

def save(s): open(FILE,"w").write(json.dumps(s))

def mk_brand(h,a,sc,lg,top,bottom):
 W,H=1080,1080; bg=(10,22,12)
 img=Image.new("RGB",(W,H),bg); d=ImageDraw.Draw(img)
 try: fb=ImageFont.truetype("DejaVuSans-Bold.ttf",100); fm=ImageFont.truetype("DejaVuSans-Bold.ttf",50); fs=ImageFont.truetype("DejaVuSans-Bold.ttf",34); fs2=ImageFont.truetype("DejaVuSans-Bold.ttf",28)
 except: fb=fm=fs=fs2=ImageFont.load_default()
 GREEN=(0,255,100)
 d.rounded_rectangle([20,15,1060,80],radius=22,fill=GREEN); d.text((35,22),f"🟢 {lg.upper()} • {top}"[:38],font=fs,fill=(0,0,0))
 d.text((50,170),h.upper()[:22],font=fm,fill=(255,255,255)); d.text((50,240),a.upper()[:22],font=fm,fill=(200,255,200))
 d.rounded_rectangle([300,430,780,570],radius=32,fill=(255,255,255)); bbox=d.textbbox((0,0),sc,font=fb); w=bbox[2]-bbox[0]; d.text(((W-w)//2,445),sc,font=fb,fill=(0,0,0))
 d.rounded_rectangle([20,990,1060,1060],radius=22,fill=GREEN); d.text((30,1000),f"🟢 Unfiltered Scores • {bottom}"[:48],font=fs2,fill=(0,0,0))
 p="/tmp/brand.jpg"; img.save(p,"JPEG",quality=95); return p

def post(msg,path):
 try:
  with open(path,"rb") as f: r=requests.post(f"https://graph.facebook.com/v20.0/{PID}/photos",data={"caption":msg,"access_token":TOK},files={"source":f},timeout=30)
  print(f"FB {r.status_code} {r.text[:500]}"); return r.status_code==200
 except Exception as e: print(f"ERR {e}"); return False

def get_sb(lg):
 try: j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/scoreboard",timeout=6).json(); return [{**e,"_code":lg,"_lname":NAMES.get(lg,lg)} for e in j.get("events",[])]
 except: return []

def main():
 st=load()
 all_ev=[]
 with ThreadPoolExecutor(max_workers=10) as ex:
  for lst in ex.map(get_sb,PR): all_ev.extend(lst)
 print(f"LIVE {len(all_ev)}")
 if not all_ev:
  print("NO LIVE GAMES RIGHT NOW - WAITING")
  save(st); return

 # FORCE POST FIRST GAME TO PROVE IT WORKS
 ev=all_ev[0]; comp=ev["competitions"][0]
 try: h=next(x for x in comp["competitors"] if x["homeAway"]=="home"); a=next(x for x in comp["competitors"] if x["homeAway"]=="away")
 except: save(st); return
 hn,an=h["team"]["displayName"],a["team"]["displayName"]; hs,as_=str(h.get("score","0")),str(a.get("score","0")); lg=ev["_lname"]
 FOLLOW="\n\n🟢 #UnfilteredScores #FollowForLive #LiveScores"
 img=mk_brand(hn,an,f"{hs}-{as_}",lg,"LIVE TEST","BRAND GREEN 🟢 WORKING")
 if post(f"🟢 TEST POST - BOT IS WORKING!\n\n{hn} {hs}-{as_} {an}\n{lg}\nWe are LIVE now!{FOLLOW}",img):
  print("FORCE POST SUCCESS - FB TOKEN OK")
  # DON'T SAVE KICK - JUST TEST
 else:
  print("FORCE POST FAILED - CHECK PAGE_ID / PAGE_ACCESS_TOKEN EXPIRED!")

 save(st)
 print("V75 DONE - IF TEST POSTED, DELETE STATE AND RUN V74 AGAIN")

if __name__=="__main__": main()
