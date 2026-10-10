import os, time, requests
FB_ID = os.getenv("FB_PAGE_ID")
FB_TOKEN = os.getenv("FB_PAGE_TOKEN")
BRAND = "🟢 Unfiltered Scores"
def post(msg):
    url = f"https://graph.facebook.com/v19.0/{FB_ID}/feed"
    r = requests.post(url, data={"message": msg, "access_token": FB_TOKEN})
    print(f"POST {r.status_code} - {r.text[:200]}")
    return r.status_code == 200

print(f"{BRAND} V8 TEST | Memory check")
# FORCE POST IMMEDIATELY
msg = f"""{BRAND} | SYSTEM ONLINE

✅ V8 GLOBAL is LIVE
Testing connection - fixtures coming next

This is a test to confirm posting works.
If you see this on Facebook, token is 100% OK.

#Football #Live"""
post(msg)

# Keep alive 5 mins to show it works
for i in range(10):
    print(f"Live check {i} - sleeping")
    time.sleep(35)
