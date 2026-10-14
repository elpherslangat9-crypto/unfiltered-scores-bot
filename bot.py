# V64.9.2 FINAL - UNRESTRICTED API + NEWS WITH PHOTOS
print("V64.9.2 UNRESTRICTED API + NEWS")
import os,json,requests,random,time
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

def api(path):
 if not API_KEY: print("NO API KEY"); return None
 try:
  r=requests.get(f"https://v3.football.api-sports.io/{path}",headers={"x-apisports-key":API_KEY},timeout=10)
  print(f"API CALL {path} STATUS {r.status_code}")
  if r.status_code==200: return r.json()
  print(r.text[:600])
 except Exception as e: print(f"API ERR {e}")
 return None

def load():
 d={"goals":{},"ht":{},"ft":{},"last":{},"kick":{},"news":[],"last_news_time":0}
 try:
  with open(FILE) as f: s=json.load(f)
  for k in d: s.setdefault(k,d[k]); return s
 except: return d
def save(s): open(FILE,"w").write(json.dumps(s))

def dl(u):
 try:
  r=requests.get(u,timeout=10,headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.sofascore.com/"})
  if r.status_code==200 and len(r.content)>3000: return Image.open(BytesIO(r.content)).convert("RGBA")
 except:0
 return None
def real_img(h,a):
 try: return dl(f"https://picsum.photos/seed/{h[:3]}{a[:3]}/1080/1350")
 except: return None
def mk(h,a,sc,lg,top,bot,g,red=False):
 W,H=1080,1350
 bg=g.convert("RGB").resize((W,H),Image.LANCZOS) if g else Image.new("RGB",(W,H),(12,12,12))
 if g: ov=Image.new("RGB",(W,H),(0,0,0)); bg=Image.blend(bg,ov,0.45)
 d=ImageDraw.Draw(bg)
 try: fb=ImageFont.truetype("DejaVuSans-Bold.ttf",90);fs=ImageFont.truetype("DejaVuSans-Bold.ttf",34);fs2=ImageFont.truetype("DejaVuSans-Bold.ttf",28)
 except: fb=fs=fs2=ImageFont.load_default()
 col=(255,0,0) if red else BRAND_GREEN
 d.rounded_rectangle([30,20,W-30,85],radius=20,fill=col);d.text((50,30),f"Unfiltered {lg} {top}"[:44],font=fs,fill=(0,0,0))
 d.rounded_rectangle([280,700,800,830],radius=30,fill=(255,255,255));d.text((340,720),sc,font=fb,fill=(0,0,0))
 d.rounded_rectangle([30,1240,W-30,1320],radius=20,fill=col);d.text((40,1252),bot[:56],font=fs2,fill=(0,0,0))
 p="/tmp/m.png";bg.save(p,quality=95);return p

def post(msg,path):
 try:
  r=requests.post(f"https://graph.facebook.com/v20.0/{PID}/photos",data={"caption":msg,"access_token":TOK},files={"source":open(path,"rb")},timeout=30)
  print(f"FB {r.status_code} {r.text[:400]}"); return r.status_code==200
 except Exception as e: print(f"FB ERR {e}"); return False

def get_all_football_news():
 arts=[]
 for lg in ["eng.1","uefa.champions","ken.1"]:
  try:
   j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/news",timeout=7).json()
   for a in j.get("articles",[])[:4]:
    img=a.get("images",[{}])[0].get("url","")
    arts.append({"title":a.get("headline",""),"desc":a.get("description","")[:120],"img":img,"link":a.get("links",{}).get("web",{}).get("href",""),"src":"ESPN","lg":lg})
  except:0
 try:
  j=requests.get("https://api.rss2json.com/v1/api.json?rss_url=http://feeds.bbci.co.uk/sport/football/rss.xml",timeout=7).json()
  for it in j.get("items",[])[:4]: arts.append({"title":it.get("title",""),"desc":it.get("description","")[:120],"img":it.get("enclosure",{}).get("link",""),"link":it.get("link",""),"src":"BBC","lg":"eng.1"})
 except:0
 seen=set();out=[]
 for a in arts:
  if not a["title"] or a["title"] in seen or len(a["title"])<10: continue
  seen.add(a["title"]); out.append(a)
 random.shuffle(out); return out[:10]

def get_sb(lg):
 try:
  j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/scoreboard",timeout=6).json()
  ev=[]
  for e in j.get("events",[]): e["_code"]=lg;e["_lname"]=NAMES.get(lg,lg);ev.append(e)
  return ev
 except: return []

def run_once(st):
 all_ev=[]
 with ThreadPoolExecutor(max_workers=6) as ex:
  for lst in ex.map(get_sb,["ken.1","uefa.champions","eng.1"]): all_ev.extend(lst)
 # UNRESTRICTED API CALL
 api_events=[]
 j=api("fixtures?live=all")
 if j:
  for f in j.get("response",[]):
   try:
    ln=f["league"]["name"].lower()
    if "kenya" in ln: lname="KPL";code="ken.1"
    elif "champions league" in ln: lname="UCL";code="uefa.champions"
    elif "premier league" in ln and "england" in ln: lname="Premier League";code="eng.1"
    else: continue
    h=f["teams"]["home"]["name"];a=f["teams"]["away"]["name"]
    hs=str(f["goals"]["home"] or 0);ass=str(f["goals"]["away"] or 0)
    stt=f["fixture"]["status"]["short"];m={"1H":"STATUS_IN_PROGRESS","2H":"STATUS_IN_PROGRESS","HT":"STATUS_HALFTIME","FT":"STATUS_FINAL","NS":"STATUS_SCHEDULED"}
    api_events.append({"id":f"apif_{f['fixture']['id']}","_code":code,"_lname":lname,"competitions":[{"status":{"type":{"name":m.get(stt,"STATUS_SCHEDULED"),"shortDetail":stt}},"competitors":[{"homeAway":"home","team":{"displayName":h},"score":hs},{"homeAway":"away","team":{"displayName":a},"score":ass}],"date":f["fixture"]["date"]}]})
   except:0
 print(f"API LIVE {len(api_events)}")
 all_ev.extend(api_events)
 live=[e for e in all_ev if e["competitions"][0]["status"]["type"]["name"] in ["STATUS_IN_PROGRESS","STATUS_HALFTIME","STATUS_FINAL"]]
 print(f"TOTAL LIVE {len(live)}")
 posted=0
 for ev in live:
  comp=ev["competitions"][0];status=comp["status"]["type"]["name"];comps=comp["competitors"]
  try: h=next(x for x in comps if x["homeAway"]=="home");a=next(x for x in comps if x["homeAway"]=="away")
  except: continue
  hn,an=h["team"]["displayName"],a["team"]["displayName"];hs,as_=str(h.get("score","0")),str(a.get("score","0"));lg=ev["_lname"]
  tag="#KPL #FKFPL #ViralKE" if lg=="KPL" else "#UCL #Football"
  ground=real_img(hn,an)
  if status in ["STATUS_IN_PROGRESS","STATUS_HALFTIME"]:
   if ev["id"] not in st["kick"]:
    img=mk(hn,an,hs+"-"+as_,lg,f"{comp['status']['type'].get('shortDetail','LIVE')}","KICK OFF",ground)
    if img and post(f"🔴 LIVE NOW {lg} {hn} {hs}-{as_} {an}\n\n{tag}",img): st["kick"][ev["id"]]=1;posted+=1
   gid=ev["id"]+"_"+hs+"-"+as_
   if gid not in st["goals"]:
    img=mk(hn,an,hs+"-"+as_,lg,comp['status']['type'].get('shortDetail','LIVE'),"Live",ground)
    if img and post(f"GOAL! {lg} {hn} {hs}-{as_} {an}\n\n{tag}",img): st["goals"][gid]=1;posted+=1
  st["last"][ev["id"]]=hs+"-"+as_
  if status=="STATUS_HALFTIME" and ev["id"] not in st["ht"]:
   img=mk(hn,an,hs+"-"+as_,lg,"HT","HALFTIME",ground)
   if img and post(f"HALFTIME {lg} {hn} {hs}-{as_} {an}\n\n{tag}",img): st["ht"][ev["id"]]=1;posted+=1
  if status=="STATUS_FINAL" and ev["id"] not in st["ft"]:
   img=mk(hn,an,hs+"-"+as_,lg,"FT","FULL TIME",ground)
   if img and post(f"FULL TIME {lg} {hn} {hs}-{as_} {an}\n\n{tag}",img): st["ft"][ev["id"]]=1;posted+=1
 # NEWS FREE
 now=time.time()
 if now - st.get("last_news_time",0) > 1800:
  news=get_all_football_news()
  print(f"NEWS {len(news)} FREE")
  for n in news[:2]:
   if n["title"] in st["news"]: continue
   lg_tag="KPL" if n["lg"]=="ken.1" else "FOOTBALL"
   gimg=dl(n["img"]) if n["img"] else real_img(n["title"][:10],n["src"])
   if not gimg: gimg=real_img("NEWS",n["src"])
   img=mk(n["src"],lg_tag,n["title"][:20],lg_tag,"NEWS",gimg)
   if img and post(f"{n['title']}\n\n{n['desc']}\n\nSource: {n['src']}\n{n['link']}",img):
    st["news"].append(n["title"]); posted+=1
    if len(st["news"])>200: st["news"]=st["news"][-100:]
  st["last_news_time"]=now
 return posted

def main():
 st=load(); tot=run_once(st); save(st); print(f"V64.9.2 DONE {tot} UNRESTRICTED+NEWS")
if __name__=="__main__": main()
