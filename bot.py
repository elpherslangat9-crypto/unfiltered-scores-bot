# V64.6 FINAL - NO LINEUP=0 BURN, LINEUP READY=BURN
print("V64.6 TWO KPL LINEUP SMART BURN 97 GREEN")
import os,json,requests,re,random,time
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image,ImageDraw,ImageFont
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
PID=os.getenv("PAGE_ID");TOK=os.getenv("PAGE_ACCESS_TOKEN") or os.getenv("FB_TOKEN")
API_KEY=os.getenv("API_FOOTBALL_KEY")
FILE="posted_state.json";EAT=ZoneInfo("Africa/Nairobi")
NAMES={"eng.1":"Premier League","ken.1":"KPL","uefa.champions":"UCL"}
BRAND_GREEN=(0,255,100)
USED=0;LIMIT=92
def api(path):
 global USED
 if not API_KEY or USED>=LIMIT: print(f"LIMIT HIT {USED}/{LIMIT} STOP LEAVE 3");return None
 try:
  r=requests.get(f"https://v3.football.api-sports.io/{path}",headers={"x-apisports-key":API_KEY},timeout=7)
  if r.status_code==200: USED+=1; print(f"API {USED}/92 BURN {path} - SMART"); return r.json()
 except:0
 return None
def load():
 d={"lineup":{},"goals":{},"ht":{},"ft":{},"last":{},"red":{},"kick":{},"news":[],"last_news_time":0,"api_lineup":{},"last_api_time":0,"lineup_ready":False}
 try:
  with open(FILE) as f: s=json.load(f)
  for k in d: s.setdefault(k,d[k]); return s
 except: return d
def save(s): open(FILE,"w").write(json.dumps(s))
def dl(u):
 try:
  r=requests.get(u,timeout=8,headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.sofascore.com/"})
  if r.status_code==200 and len(r.content)>3000: return Image.open(BytesIO(r.content)).convert("RGBA")
 except:0
 return None
def real_img(h,a):
 try:
  im=dl(f"https://picsum.photos/seed/{h[:3]}{a[:3]}/1080/1350")
  if im: return im
 except:0
 return None
def mk(h,a,sc,lg,top,bot,g,face=None,red=False):
 W,H=1080,1350
 bg=None
 if g:
  try: bg=g.convert("RGB").resize((W,H),Image.LANCZOS);ov=Image.new("RGB",(W,H),(0,0,0));bg=Image.blend(bg,ov,0.45)
  except:0
 if bg is None: bg=Image.new("RGB",(W,H),(12,12,12))
 d=ImageDraw.Draw(bg)
 try: fb=ImageFont.truetype("DejaVuSans-Bold.ttf",90);fs=ImageFont.truetype("DejaVuSans-Bold.ttf",34);fs2=ImageFont.truetype("DejaVuSans-Bold.ttf",28)
 except: fb=fs=fs2=ImageFont.load_default()
 header_col=BRAND_GREEN if not red else (255,0,0)
 d.rounded_rectangle([30,20,W-30,85],radius=20,fill=header_col);d.text((50,30),(f"Unfiltered {lg} {top}")[:44],font=fs,fill=(0,0,0))
 d.rounded_rectangle([280,700,800,830],radius=30,fill=(255,255,255));d.text((340,720),sc,font=fb,fill=(0,0,0))
 d.rounded_rectangle([30,1240,W-30,1320],radius=20,fill=header_col);d.text((40,1252),bot[:56],font=fs2,fill=(0,0,0))
 p="/tmp/m.png";bg.save(p,quality=95);return p
def post(msg,path):
 try:
  r=requests.post(f"https://graph.facebook.com/v20.0/{PID}/photos",data={"caption":msg,"access_token":TOK},files={"source":open(path,"rb")},timeout=20)
  print(f"FB {r.status_code}");return r.status_code==200
 except Exception as e: print(f"FB ERR {e}");return False
def get_sb(lg):
 try:
  j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/scoreboard",timeout=5).json()
  ev=[]
  for e in j.get("events",[]): e["_code"]=lg;e["_lname"]=NAMES.get(lg,lg);ev.append(e)
  return ev
 except: return []
def get_fast():
 ev=[];H={"User-Agent":"Mozilla/5.0","Referer":"https://www.sofascore.com/"}
 try:
  r=requests.get("https://api.sofascore.app/api/v1/sport/football/events/live",timeout=7,headers=H)
  j=r.json()
  for e in j.get("events",[]):
   tour=(e.get("tournament",{}).get("name","")+e.get("tournament",{}).get("category",{}).get("name","")).lower()
   code=None;lname=None
   if "kenya" in tour: code="ken.1";lname="KPL"
   elif "champions" in tour: code="uefa.champions";lname="UCL"
   elif "premier league" in tour: code="eng.1";lname="Premier League"
   if not code: continue
   hs=str(e.get("homeScore",{}).get("current",0));ass=str(e.get("awayScore",{}).get("current",0))
   st=e.get("status",{}).get("type","");st_map={"inprogress":"STATUS_IN_PROGRESS","halftime":"STATUS_HALFTIME","finished":"STATUS_FINAL"}
   stype=st_map.get(st,"STATUS_SCHEDULED");mn=e.get("time",{}).get("minute",0)
   ev.append({"id":"sofa_"+str(e.get('id')),"_code":code,"_lname":lname,"competitions":[{"status":{"type":{"name":stype,"shortDetail":f"{mn}'"}},"competitors":[{"homeAway":"home","team":{"displayName":e.get("homeTeam",{}).get("name","")},"score":hs},{"homeAway":"away","team":{"displayName":e.get("awayTeam",{}).get("name","")},"score":ass}],"date":""}]})
  return ev
 except: return []
def should_use_api(live_events, st):
 # BOSS RULE: LIVE always burns, LINEUP ready also burns, else 0
 for ev in live_events:
  s=ev["competitions"][0]["status"]["type"]["name"]
  if s in ["STATUS_IN_PROGRESS","STATUS_HALFTIME"]:
   print("USE API - LIVE NOW")
   return True
 # Check if game soon (within 2h) AND lineup_ready flag true
 try:
  soon=False
  for ev in live_events:
   ds=ev["competitions"][0].get("date","")
   if not ds: continue
   dt=datetime.fromisoformat(ds.replace("Z","+00:00")).astimezone(EAT)
   hrs=(dt - datetime.now(EAT)).total_seconds()/3600
   if 0<=hrs<=2: soon=True
  if soon and st.get("lineup_ready"):
   print("USE API - LINEUP READY - BURN")
   return True
  if soon and not st.get("lineup_ready"):
   print("NO LINEUP YET - 0 BURN - SAVING")
   # Try ONE cheap check every 30 mins if lineup now ready
   now=time.time()
   if now - st.get("last_api_time",0) > 1800: # 30 min check
    j=api("fixtures?date="+datetime.now(EAT).strftime("%Y-%m-%d"))
    st["last_api_time"]=now
    if j:
     for f in j.get("response",[]):
      if f.get("lineups") and len(f["lineups"])>0:
       st["lineup_ready"]=True
       print("LINEUP FOUND - WILL BURN FROM NOW")
       return True
   return False
 except Exception as e: print(f"ERR {e}")
 return False
def run_once(st):
 all_ev=[]
 with ThreadPoolExecutor(max_workers=6) as ex:
  for lst in ex.map(get_sb,["ken.1","uefa.champions","eng.1"]): all_ev.extend(lst)
 free_live=[e for e in all_ev if e["competitions"][0]["status"]["type"]["name"] in ["STATUS_IN_PROGRESS","STATUS_HALFTIME"]]
 use_api=should_use_api(all_ev, st)
 api_events=[]
 if use_api:
  j=api("fixtures?live=all")
  if j:
   for f in j.get("response",[]):
    try:
     league=f["league"]["name"].lower()
     if "kenya" in league: lname="KPL";code="ken.1"
     elif "champions league" in league: lname="UCL";code="uefa.champions"
     else: continue
     h=f["teams"]["home"]["name"];a=f["teams"]["away"]["name"]
     hs=str(f["goals"]["home"] or 0);ass=str(f["goals"]["away"] or 0)
     stt=f["fixture"]["status"]["short"];st_map={"1H":"STATUS_IN_PROGRESS","2H":"STATUS_IN_PROGRESS","HT":"STATUS_HALFTIME","FT":"STATUS_FINAL","NS":"STATUS_SCHEDULED"}
     stype=st_map.get(stt,"STATUS_SCHEDULED")
     api_events.append({"id":f"apif_{f['fixture']['id']}","_code":code,"_lname":lname,"_apif_id":f["fixture"]["id"],"competitions":[{"status":{"type":{"name":stype,"shortDetail":stt}},"competitors":[{"homeAway":"home","team":{"displayName":h},"score":hs},{"homeAway":"away","team":{"displayName":a},"score":ass}],"date":f["fixture"]["date"]}]})
    except:0
   print(f"API LIVE {len(api_events)} - 2 KPL TODAY")
 else: print(f"SKIPPED API - FREE LIVE {len(free_live)} - SMART SAVE")
 all_ev.extend(api_events); all_ev.extend(get_fast())
 live=[e for e in all_ev if e["competitions"][0]["status"]["type"]["name"] in ["STATUS_IN_PROGRESS","STATUS_HALFTIME","STATUS_SCHEDULED","STATUS_FINAL"]]
 print(f"TOTAL LIVE {len(live)} (2 KPL TODAY) API USED {USED}/92")
 posted=0
 for ev in live:
  comp=ev["competitions"][0];status=comp["status"]["type"]["name"];comps=comp["competitors"]
  try: h=next(x for x in comps if x["homeAway"]=="home");a=next(x for x in comps if x["homeAway"]=="away")
  except: continue
  hn,an=h["team"]["displayName"],a["team"]["displayName"];hs,as_=str(h.get("score","0")),str(a.get("score","0"));lg=ev["_lname"]
  tag="#KPL #FKFPL #ViralKE 🟢" if lg=="KPL" else "#UCL #ChampionsLeague #Viral 🟢"
  ground=real_img(hn,an); last=st.get("last",{}).get(ev["id"],"0-0")
  if status in ["STATUS_IN_PROGRESS","STATUS_HALFTIME"] and last!=hs+"-"+as_ and not (last=="0-0" and hs=="0" and as_=="0"):
   gid=ev["id"]+"_"+hs+"-"+as_
   if gid not in st["goals"]:
    img=mk(hn,an,hs+"-"+as_,lg,f"{comp['status']['type'].get('shortDetail','LIVE')}","Live",ground)
    if img and post(f"GOAL! 🟢 {lg} {hn} {hs}-{as_} {an}\n\n{tag}",img): st["goals"][gid]=1;posted+=1
  st["last"][ev["id"]]=hs+"-"+as_
  if status=="STATUS_HALFTIME" and ev["id"] not in st["ht"]:
   img=mk(hn,an,hs+"-"+as_,lg,"HT","HALFTIME",ground)
   if img and post(f"HALFTIME 🟢 {lg} {hn} {hs}-{as_} {an}\n\n{tag}",img): st["ht"][ev["id"]]=1;posted+=1
  if status=="STATUS_FINAL" and ev["id"] not in st["ft"]:
   img=mk(hn,an,hs+"-"+as_,lg,"FT","FULL TIME",ground)
   if img and post(f"FULL TIME 🟢 {lg} {hn} {hs}-{as_} {an}\n\n{tag}",img): st["ft"][ev["id"]]=1;posted+=1
 return posted
def main():
 st=load(); tot=run_once(st); save(st); print(f"V64.6 DONE {tot} API USED {USED}/92 LEAVE 3 - SMART")
if __name__=="__main__": main()
