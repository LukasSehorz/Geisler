#!/usr/bin/env python3
"""KIE.ai client: upload, createTask, poll, download (Geissler)."""
import base64, io, json, mimetypes, os, sys, time, urllib.request, urllib.error
KEY = os.environ.get("KIE_KEY", "")  # set KIE_KEY in your environment – never commit the key
API = "https://api.kie.ai/api/v1"
UPLOAD = "https://kieai.redpandaai.co/api/file-base64-upload"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json", "User-Agent": UA, "Accept": "application/json"}
CACHE = os.path.join(os.path.dirname(__file__), "upload_cache.json")
import threading
_LOCK = threading.Lock()

def _post(url, payload, timeout=180):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=H, method="POST")
    try:
        return json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    except urllib.error.HTTPError as e:
        return {"code": e.code, "msg": e.read().decode()[:500]}

def _get(url, timeout=60):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {KEY}", "User-Agent": UA})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    except urllib.error.HTTPError as e:
        return {"code": e.code, "msg": e.read().decode()[:500]}

def credits():
    return (_get(f"{API}/chat/credit") or {}).get("data")

def upload(path, max_side=1800):
    key = f"{os.path.abspath(path)}::{os.path.getmtime(path)}::{max_side}"
    with _LOCK:
        cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
        if key in cache:
            return cache[key]
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    im.thumbnail((max_side, max_side))
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=92)
    b64 = base64.b64encode(buf.getvalue()).decode()
    name = os.path.splitext(os.path.basename(path))[0][:60] + ".jpg"
    r = _post(UPLOAD, {"base64Data": f"data:image/jpeg;base64,{b64}", "uploadPath": "images/geissler", "fileName": name})
    url = (r.get("data") or {}).get("downloadUrl")
    if not url:
        raise RuntimeError(f"Upload failed: {r}")
    with _LOCK:
        cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
        cache[key] = url
        tmp = CACHE + ".tmp"; json.dump(cache, open(tmp, "w"), indent=1); os.replace(tmp, CACHE)
    return url

def create(model, inp):
    r = _post(f"{API}/jobs/createTask", {"model": model, "input": inp})
    tid = (r.get("data") or {}).get("taskId")
    if not tid:
        raise RuntimeError(f"createTask failed: {r}")
    return tid

def wait(task_id, timeout=1800, every=10):
    t0 = time.time(); last = None
    while time.time() - t0 < timeout:
        r = _get(f"{API}/jobs/recordInfo?taskId={task_id}")
        d = r.get("data") or {}
        state = d.get("state") or d.get("status")
        if state != last:
            print(f"   [{int(time.time()-t0):>4}s] {task_id[:14]} {state}", flush=True); last = state
        if state in ("success", "completed"):
            res = d.get("resultJson") or d.get("result") or "{}"
            return json.loads(res) if isinstance(res, str) else res
        if state in ("fail", "failed", "error"):
            raise RuntimeError(f"Task failed: {d.get('failMsg') or d}")
        time.sleep(every)
    raise TimeoutError(task_id)

def download(url, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    data = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=600).read()
    open(dest, "wb").write(data)
    print(f"   -> {dest} ({len(data)/1024:.0f} KB)", flush=True)
    return dest

def run(model, inp, dest):
    tid = create(model, inp)
    print(f"   task {tid} ({model}) -> {os.path.basename(dest)}", flush=True)
    res = wait(tid)
    urls = res.get("resultUrls") or res.get("urls") or []
    if isinstance(urls, str): urls = [urls]
    if not urls: raise RuntimeError(f"no result url: {res}")
    download(urls[0], dest)
    return urls[0]

def image(prompt, dest, refs=None, ar="16:9", res="2K"):
    if refs:
        return run("gpt-image-2-image-to-image", {"prompt": prompt, "input_urls": [upload(r) if not r.startswith("http") else r for r in refs], "aspect_ratio": ar, "resolution": res}, dest)
    return run("gpt-image-2-text-to-image", {"prompt": prompt, "aspect_ratio": ar, "resolution": res}, dest)

def batch(jobs, workers=6):
    """jobs: list of dicts with keys for image(); runs concurrently, skips existing dest."""
    from concurrent.futures import ThreadPoolExecutor
    def one(j):
        if os.path.exists(j["dest"]):
            print("skip", j["dest"]); return j["dest"], "exists"
        for attempt in range(3):
            try:
                return j["dest"], image(**j)
            except Exception as e:
                print("ERR", os.path.basename(j["dest"]), attempt, str(e)[:300], flush=True)
                time.sleep(5)
        return j["dest"], None
    with ThreadPoolExecutor(workers) as ex:
        return list(ex.map(one, jobs))

if __name__ == "__main__":
    print(credits())
