# ASCII-only helper: download given date folders from this repo into ~/Desktop/<album dir>
# usage: python fetch.py 2026-01-04 2026-01-11 ...   (existing files are never overwritten)
import json, os, sys, time, urllib.request, urllib.parse
REPO = os.environ.get("AES_REPO", "57cx/aesthetic-weekly")
ROOT = os.path.join(os.path.expanduser("~"), "Desktop", "\u5ba1\u7f8e\u63d0\u5347")
UA = {"User-Agent": "aes-fetch"}
def get(u, t=120):
    for a in range(5):
        try:
            return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=t).read()
        except Exception as e:
            err = e; time.sleep(5 + 10 * a)
    raise err
dates = sys.argv[1:]
tree = json.loads(get("https://api.github.com/repos/%s/git/trees/main?recursive=1" % REPO))["tree"]
files = [x for x in tree if x["type"] == "blob" and x["path"].split("/")[0] in dates]
ok = skip = bad = 0
for x in files:
    dst = os.path.join(ROOT, *x["path"].split("/"))
    if os.path.exists(dst):
        if os.path.getsize(dst) == x["size"]: skip += 1
        else: bad += 1; print("EXISTS-DIFF (not overwritten):", x["path"].encode("unicode_escape").decode())
        continue
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    b = get("https://raw.githubusercontent.com/%s/main/%s" % (REPO, urllib.parse.quote(x["path"])))
    if len(b) != x["size"]:
        b = get("https://raw.githubusercontent.com/%s/main/%s" % (REPO, urllib.parse.quote(x["path"])))
    open(dst + ".part", "wb").write(b); os.replace(dst + ".part", dst); ok += 1
for d in dates:
    n = 0; s = 0
    for r, _, fs in os.walk(os.path.join(ROOT, d)):
        for f in fs: n += 1; s += os.path.getsize(os.path.join(r, f))
    exp = [x for x in files if x["path"].split("/")[0] == d]
    print("CHECK", d, "pc_files", n, "pc_bytes", s, "repo_files", len(exp), "repo_bytes", sum(x["size"] for x in exp), "MATCH" if n == len(exp) and s == sum(x["size"] for x in exp) else "MISMATCH")
print("downloaded", ok, "skipped", skip, "diff", bad)
