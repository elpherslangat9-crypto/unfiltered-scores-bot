# V-ULTIMATE - ALL SOURCES - FOOTBALL ONLY - LINEUPS RED PENALTY - HD NEWS
print("V-ULTIMATE ALL SOURCES LOADED")
import os,json,requests,re,time,xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

PID=os.getenv("PAGE_ID"); TOK=os.getenv("PAGE_ACCESS_TOKEN") or os.getenv("FB_TOKEN")
FILE="posted_state.json"

NAMES={"eng.1":"Premier League","esp.1":"LaLiga","ger.1":"Bundesliga","ita.1":"Serie A","fra.1":"Ligue 1","ken.1":"FKF Premier League","usa.1":"MLS","uefa.champions":"UCL","uefa.europa":"Europa"}
LEAGUES=list(NAMES.keys())

FOLLOW_LIVE="\n\n🟢 FOLLOW Unfiltered Scores for LIVE Goals!\n🔔 Turn ON Notifications\n\n#UnfilteredScores #LiveScores #FootballLive #FollowForMore #PremierLeague #LaLiga #LiveFootball"
FOLLOW_NEWS="\n\n🟢 Follow for 24/7 Football News\n\n#UnfilteredScores #FootballNews #TransferNews #BreakingNews"

# ---------- STATE ----------
def load():
 try:
  d=json.load(open(FILE))
  return {"kick":d.get("kick",{}),"goals":d.get("goals",{}),"ht":d.get("ht",{}),"ft":d.get("ft",{}),"red":d.get("red",{}),"pen":d.get("pen",{}),"lineup":d.get("lineup",{}),"news":d.get("news",[]),"last":d.get("last",{})}
 except: return {"kick":{},"goals":{},"ht":{},"ft":{},"red":{},"pen":{},"lineup":{},"news":[],"last":{}}
def save(s):
 try: open(FILE,"w").write(json.dumps(s))
 except: pass

# ---------- FB ----------
def fb_text(msg):
 try:
  r=requests.post(f"https://graph.facebook.com/v20.0/{PID}/feed",data={"message":msg,"access_token":TOK},timeout=15)
  print(f"FB TEXT {r.status_code}"); return r.status_code==200
 except Exception as e: print(f"FB ERR {e}"); return False

def fb_photo(msg,img_url):
 try:
  # clean HD image - filter small images
  if not img_url or ".svg" in img_url: return False
  data=requests.get(img_url,timeout=12,headers={"User-Agent":"Mozilla/5.0"}).content
  if len(data)<20000: # too small = not clean
   print("IMAGE TOO SMALL SKIP"); return False
  open("/tmp/news.jpg","wb").write(data)
  with open("/tmp/news.jpg","rb") as f:
   r=requests.post(f"https://graph.facebook.com/v20.0/{PID}/photos",data={"caption":msg,"access_token":TOK},files={"source":f},timeout=25)
  print(f"FB PHOTO {r.status_code} {r.text[:300]}"); return r.status_code==200
 except Exception as e: print(f"PHOTO ERR {e}"); return False

# ---------- SCORES FROM ALL SOURCES ----------
def get_espn_scoreboard(lg):
 try:
  j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/scoreboard",timeout=5).json()
  return [{**e,"_code":lg,"_lname":NAMES.get(lg,lg)} for e in j.get("events",[])]
 except: return []

def get_match_details(lg,eid):
 # Gets lineups, red cards, penalties from ESPN summary - THIS IS LIVESCORES SOURCE
 try:
  url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/summary?event={eid}"
  j=requests.get(url,timeout=5).json()
  return j
 except: return {}

# ---------- NEWS FROM ALL SOURCES - FOOTBALL FILTERED ----------
def fetch_rss(url, source_name):
 items=[]
 try:
  r=requests.get(url,timeout=7,headers={"User-Agent":"Mozilla/5.0"}).text
  root=ET.fromstring(r)
  for it in root.findall(".//item")[:15]:
   title=(it.findtext("title") or "").strip()
   link=(it.findtext("link") or "").strip()
   desc=(it.findtext("description") or "")[:250]
   # image from enclosure or media
   img=""
   enc=it.find("enclosure");
   if enc is not None: img=enc.attrib.get("url","")
   if not img:
    media=it.find("{http://search.yahoo.com/mrss/}content")
    if media is not None: img=media.attrib.get("url","")
    # try media thumbnail
    if not img:
     thumb=it.find("{http://search.yahoo.com/mrss/}thumbnail")
     if thumb is not None: img=thumb.attrib.get("url","")
   # FILTER FOOTBALL ONLY
   ft=title.lower()+desc.lower()
   if any(k in ft for k in ["football","premier","laliga","uefa","fifa","goal","transfer","manchester","arsenal","liverpool","real madrid","barcelona","champions","league","soccer","striker","midfield"]):
    items.append({"title":title,"link":link,"desc":desc,"img":img,"source":source_name})
 except Exception as e: print(f"RSS {source_name} ERR {e}")
 return items

def get_all_football_news():
 all_news=[]
 sources=[
  ("https://feeds.bbci.co.uk/sport/football/rss.xml","BBC Football"),
  ("https://www.skysports.com/rss/12040","Sky Sports"),
  ("https://www.goal.com/en/feeds/news","Goal.com")
 ]
 with ThreadPoolExecutor(max_workers=3) as ex:
  futs=[ex.submit(fetch_rss,url,name) for url,name in sources]
  for f in futs:
   all_news.extend(f.result())
 # + ESPN news
 try:
  j=requests.get("https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/news",timeout=5).json()
  for a in j.get("articles",[])[:8]:
   img=a.get("images",[{}])[0].get("url","") if a.get("images") else ""
   all_news.append({"title":a.get("headline",""),"link":a.get("links",{}).get("web",{}).get("href",""),"desc":a.get("description","")[:250],"img":img,"source":"ESPN"})
 except: pass
 # dedup by title
 seen=set(); uniq=[]
 for n in all_news:
  if n["title"][:30] not in seen:
   seen.add(n["title"][:30]); uniq.append(n)
 return uniq[:20]

# ---------- MAIN ----------
def main():
 st=load()
 print(f"STATE loaded")

 # 1. GET ALL LIVE GAMES FROM MULTIPLE SOURCES
 all_ev=[]
 with ThreadPoolExecutor(max_workers=12) as ex:
  for lst in ex.map(get_espn_scoreboard, LEAGUES):
   all_ev.extend(lst)
 print(f"TOTAL LIVE EVENTS {len(all_ev)}")

 posted=0
 # Check each live game for details (lineups, red, pen)
 for ev in all_ev:
  if posted>=4: break
  try:
   eid=ev["id"]; lg=ev["_code"]; comp=ev["competitions"][0]
   status=comp["status"]["type"]["name"]
   detail=comp["status"]["type"]["shortDetail"]
   home=next(x for x in comp["competitors"] if x["homeAway"]=="home")
   away=next(x for x in comp["competitors"] if x["homeAway"]=="away")
   hn,an=home["team"]["displayName"],away["team"]["displayName"]
   hs,as_=str(home.get("score","0")),str(away.get("score","0"))
   score=f"{hs}-{as_}"
   lgname=ev["_lname"]
   last=st["last"].get(eid,"")

   # GET DETAILS FOR RED CARDS / PENALTY / LINEUPS
   details=get_match_details(lg,eid)
   # parse red cards and penalties from details if available
   red_events=[]
   pen_events=[]
   try:
    # ESPN key events
    for k in details.get("header",{}).get("competitions",[{}])[0].get("competitors",[]):
     pass
    # Look for commentary or key events
    for item in details.get("commentary",[]):
     txt=item.get("text","").lower()
     if "red card" in txt: red_events.append(item.get("text"))
     if "penalty" in txt: pen_events.append(item.get("text"))
   except: pass

   # KICKOFF
   if status in ["STATUS_IN_PROGRESS","STATUS_FIRST_HALF"] and eid not in st["kick"]:
    msg=f"🟢 KICK-OFF LIVE NOW!\n\n{hn} vs {an}\n🏆 {lgname}\n⏱️ {detail}\n\nPredict the score! 👇{FOLLOW_LIVE}"
    if fb_text(msg): st["kick"][eid]=True; st["last"][eid]=score; posted+=1; continue

   # GOAL
   if last and last!=score and status!="STATUS_HALFTIME":
    if st["goals"].get(eid)!=score:
     msg=f"⚽️ GOAL ALERT! {score}\n\n{hn} {hs} - {as_} {an}\n🏆 {lgname}\n⏱️ {detail}\n\nLive updates every minute!{FOLLOW_LIVE}"
     if fb_text(msg): st["goals"][eid]=score; st["last"][eid]=score; posted+=1; continue
   st["last"][eid]=score

   # RED CARD
   if red_events and eid not in st["red"]:
    msg=f"🔴 RED CARD!\n\n{hn} vs {an}\n{red_events[0]}\n🏆 {lgname}\n⏱️ {detail}\nScore: {score}{FOLLOW_LIVE}"
    if fb_text(msg): st["red"][eid]=True; posted+=1; continue

   # PENALTY
   if pen_events and eid not in st["pen"]:
    msg=f"🎯 PENALTY!\n\n{hn} vs {an}\n{pen_events[0]}\n🏆 {lgname}\n⏱️ {detail}{FOLLOW_LIVE}"
    if fb_text(msg): st["pen"][eid]=True; posted+=1; continue

   # HALFTIME
   if status=="STATUS_HALFTIME" and eid not in st["ht"]:
    msg=f"⏸️ HALF TIME\n\n{hn} {hs} - {as_} {an}\n🏆 {lgname}\n\nSecond half live soon!{FOLLOW_LIVE}"
    if fb_text(msg): st["ht"][eid]=True; posted+=1; continue

   # FULLTIME
   if status in ["STATUS_FULL_TIME","STATUS_FINAL"] and eid not in st["ft"]:
    msg=f"✅ FULL TIME\n\n{hn} {hs} - {as_} {an}\n🏆 {lgname}\n\nYour MOTM? 👇{FOLLOW_LIVE}"
    if fb_text(msg): st["ft"][eid]=True; posted+=1; continue

   # LINEUPS (once per match)
   if status in ["STATUS_IN_PROGRESS","STATUS_FIRST_HALF"] and eid not in st["lineup"]:
    try:
     # try get lineups from details
     lineups=details.get("lineups",[])
     if lineups:
      msg=f"📋 LINE-UPS\n\n{hn} vs {an}\n🏆 {lgname}\n\nLineups confirmed! Kick-off live!{FOLLOW_LIVE}"
      if fb_text(msg): st["lineup"][eid]=True; posted+=1; continue
    except: pass

  except Exception as e: print(f"EV ERR {e}"); continue

 # 2. NEWS IF NO LIVE POST - FROM ALL SOURCES WITH HD PHOTOS
 if posted==0:
  news_list=get_all_football_news()
  print(f"NEWS TOTAL {len(news_list)}")
  for n in news_list:
   nid=n["title"][:60]
   if nid in st["news"]: continue
   title=n["title"]; link=n["link"]; desc=n["desc"]; img=n["img"]; src=n["source"]
   msg=f"🗞️ {src.upper()} | FOOTBALL NEWS\n\n{title}\n\n{desc}\n\n🔗 {link}{FOLLOW_NEWS}"
   ok=False
   if img and len(img)>10:
    # ensure clean clear image
    ok=fb_photo(msg,img)
   if not ok:
    ok=fb_text(msg)
   if ok:
    st["news"].append(nid); st["news"]=st["news"][-150:]; posted+=1; break

 save(st)
 print(f"V-ULTIMATE DONE POSTED {posted}")

if __name__=="__main__":
 if not PID or not TOK: print("MISSING SECRETS")
 else: main()
