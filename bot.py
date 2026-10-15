# V74 BRAND GREEN RETAINED - NO EXTERNAL PHOTO - BRANDED TEXT IMAGE - NEVER MISS 5 PER RUN
print("V74 BRAND GREEN LOADED")
import os,json,requests,re,time
from PIL import Image,ImageDraw,ImageFont
from concurrent.futures import ThreadPoolExecutor

PID=os.getenv("PAGE_ID");TOK=os.getenv("PAGE_ACCESS_TOKEN") or os.getenv("FB_TOKEN")
FILE="posted_state.json"
NAMES={"eng.1":"Premier League","esp.1":"LaLiga","ger.1":"Bundesliga","ita.1":"Serie A","fra.1":"Ligue 1","ken.1":"KPL","usa.1":"MLS","uefa.champions":"UCL","uefa.europa":"Europa","eng.2":"Championship"}
PR=list(NAMES.keys())
BIG=["Premier League","KPL","UCL"]
BADP=["lens","sporting cp","slavia praha","goal scorer","unknown"]

def load():
 d={"last":{},"goals":{},"ht":{},"ft":{},"red":{},"kick":{},"news":[]}
 try: return {**d,**json.load(open(FILE))}
 except: return d
def save(s): open(FILE,"w").write(json.dumps(s))

def mk_brand(h,a,sc,lg,top,bottom,red=False):
 # YOUR BRAND 🟢 - DARK (10,22,12) + NEON GREEN (0,255,100)
 W,H=1080,1080
 bg=(10,22,12) if not red else (60,12,12)
 img=Image.new("RGB",(W,H),bg)
 d=ImageDraw.Draw(img)
 try:
  fb=ImageFont.truetype("DejaVuSans-Bold.ttf",100)
  fm=ImageFont.truetype("DejaVuSans-Bold.ttf",50)
  fs=ImageFont.truetype("DejaVuSans-Bold.ttf",34)
  fs2=ImageFont.truetype("DejaVuSans-Bold.ttf",30)
 except: fb=fm=fs=fs2=ImageFont.load_default()
 GREEN=(0,255,100)
 RED=(255,40,40)
 col=RED if red else GREEN
 # Top brand bar
 d.rounded_rectangle([20,15,1060,80],radius=22,fill=col)
 d.text((35,22),f"🟢 {lg.upper()} • {top}"[:38],font=fs,fill=(0,0,0))
 # Teams
 d.text((50,170),h.upper()[:22],font=fm,fill=(255,255,255))
 d.text((50,240),a.upper()[:22],font=fm,fill=(200,255,200) if not red else (255,200,200))
 # Score box - white
 d.rounded_rectangle([300,430,780,570],radius=32,fill=(255,255,255))
 # Center score
 bbox=d.textbbox((0,0),sc,font=fb);w=bbox[2]-bbox[0];d.text(((W-w)//2,445),sc,font=fb,fill=(0,0,0))
 # Bottom brand bar
 d.rounded_rectangle([20,990,1060,1060],radius=22,fill=col)
 d.text((30,1000),f"🟢 Unfiltered Scores • {bottom}"[:48],font=fs2,fill=(0,0,0))
 p="/tmp/brand.jpg";img.save(p,"JPEG",quality=95);return p

def post(msg,path):
 try:
  with open(path,"rb") as f:
   r=requests.post(f"https://graph.facebook.com/v20.0/{PID}/photos",data={"caption":msg,"access_token":TOK},files={"source":f},timeout=30)
  print(f"FB {r.status_code} {r.text[:350]}")
  return r.status_code==200
 except Exception as e: print(f"ERR {e}");return False

def get_sb(lg):
 try: j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/scoreboard",timeout=6).json();return [{**e,"_code":lg,"_lname":NAMES.get(lg,lg)} for e in j.get("events",[])]
 except: return []
def get_sum(ar):
 eid,code=ar
 try: j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/summary?event={eid}",timeout=6).json();return {"d":j.get("header",{}).get("competitions",[{}])[0].get("details",[]) or []}
 except: return {"d":[]}

def main():
 st=load()
 all_ev=[]
 with ThreadPoolExecutor(max_workers=10) as ex:
  for lst in ex.map(get_sb,PR): all_ev.extend(lst)
 print(f"LIVE {len(all_ev)}")
 sums={}
 with ThreadPoolExecutor(max_workers=12) as ex:
  ids=[(e["id"],e["_code"]) for e in all_ev]
  for e,s in zip(all_ev, ex.map(get_sum, ids)): sums[e["id"]]=s

 posted=0
 MAX=5 # 5 PER RUN = NEVER MISS BUT NO 400
 for ev in all_ev:
  if posted>=MAX: break
  eid=ev["id"];comp=ev["competitions"][0];status=comp["status"]["type"]["name"];short=comp["status"]["type"].get("shortDetail","")
  try: h=next(x for x in comp["competitors"] if x["homeAway"]=="home");a=next(x for x in comp["competitors"] if x["homeAway"]=="away")
  except: continue
  hn,an=h["team"]["displayName"],a["team"]["displayName"];hs,as_=str(h.get("score","0")),str(a.get("score","0"));lg=ev["_lname"]
  FOLLOW="\n\n🟢 #UnfilteredScores #FollowForLive #LiveScores #FootballKE #Viral"
  m=re.search(r"(\d+)'",short);minute=int(m.group(1)) if m else 0
  last=st.get("last",{}).get(eid,"0-0")

  if status in ["STATUS_IN_PROGRESS","STATUS_HALFTIME"] and eid not in st["kick"]:
   img=mk_brand(hn,an,"0-0",lg,"KICK OFF","KICK OFF - FOLLOW US")
   if post(f"🟢 KICK OFF!\n\n{hn} vs {an}\n{lg}{FOLLOW}",img): st["kick"][eid]=1;posted+=1;save(st);time.sleep(5);continue

  if status in ["STATUS_IN_PROGRESS","STATUS_HALFTIME"] and last!=f"{hs}-{as_}":
   if not (last=="0-0" and hs=="0" and as_=="0"):
    gid=eid+"_"+f"{hs}-{as_}"
    if gid not in st["goals"]:
     pname=""
     for d in sums.get(eid,{}).get("d",[])[-5:]:
      if "goal" in str(d.get("type","")).lower():
       cand=d.get("athlete",{}).get("displayName","")
       if cand and cand.lower() not in BADP: pname=cand;break
     if pname and pname.lower() not in BADP:
      img=mk_brand(hn,an,f"{hs}-{as_}",lg,f"{minute}' GOAL",f"{pname} {minute}'")
      if post(f"🟢 GOAL! {minute}' {pname}\n\n{hn} {hs}-{as_} {an}\n{lg}{FOLLOW}",img): st["goals"][gid]=1;posted+=1;save(st);time.sleep(5);continue
  st["last"][eid]=f"{hs}-{as_}"
  if lg in BIG and status=="STATUS_HALFTIME" and eid not in st["ht"]:
   img=mk_brand(hn,an,f"{hs}-{as_}",lg,"HT","HALFTIME")
   if post(f"🟢 HALFTIME\n\n{hn} {hs}-{as_} {an}\n{lg}{FOLLOW}",img): st["ht"][eid]=1;posted+=1;save(st);time.sleep(5);continue
  if lg in BIG and status=="STATUS_FINAL" and eid not in st["ft"]:
   img=mk_brand(hn,an,f"{hs}-{as_}",lg,"FT","FULL TIME")
   if post(f"🟢 FULL TIME\n\n{hn} {hs}-{as_} {an}\n{lg}{FOLLOW}",img): st["ft"][eid]=1;posted+=1;save(st);time.sleep(5);continue

 print(f"V74 BRAND DONE {posted}/{MAX}");save(st)

if __name__=="__main__": main()
