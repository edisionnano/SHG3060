import socket, hmac, hashlib, time, json, base64, re, gzip, zlib, urllib.parse
from cryptography.hazmat.primitives.ciphers.aead import AESCCM

HOST, USER, PWD = "192.168.2.1", "vodafone", "Spiros123!"
UA = "Mozilla/5.0 (X11; Linux x86_64; rv:152.0) Gecko/20100101 Firefox/152.0"
COOKIES = {}

BASE = {"Accept-Language": "en-US,en;q=0.9", "Accept-Encoding": "gzip, deflate",
        "Sec-GPC": "1", "Connection": "close", "Pragma": "no-cache", "Cache-Control": "no-cache"}
PAGE = {**BASE, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Upgrade-Insecure-Requests": "1"}
XHR = {**BASE, "Accept": "application/json, text/javascript, */*; q=0.01",
       "X-Requested-With": "XMLHttpRequest", "Referer": f"http://{HOST}/login.html"}
POST = {**XHR, "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": f"http://{HOST}"}

def req(method, path, hdrs, body=None):
    h = {"Host": HOST, "User-Agent": UA, **hdrs}
    if COOKIES:
        h["Cookie"] = "; ".join(f"{k}={v}" for k, v in COOKIES.items())
    b = (body or "").encode()
    if body is not None:
        h["Content-Length"] = str(len(b))
    raw = f"{method} {path} HTTP/1.1\r\n" + "".join(f"{k}: {v}\r\n" for k, v in h.items()) + "\r\n"
    s = socket.create_connection((HOST, 80), timeout=8)
    s.sendall(raw.encode("latin1") + b)
    buf = b""
    while True:
        d = s.recv(4096)
        if not d:
            break
        buf += d
    s.close()
    head, _, body_b = buf.partition(b"\r\n\r\n")
    ht = head.decode("latin1")
    for line in ht.split("\r\n"):
        if line.lower().startswith("set-cookie:"):
            k, v = line.split(":", 1)[1].strip().split(";", 1)[0].split("=", 1)
            COOKIES[k.strip()] = v.strip()
    if "content-encoding: gzip" in ht.lower():
        body_b = gzip.decompress(body_b)
    elif "content-encoding: deflate" in ht.lower():
        try:
            body_b = zlib.decompress(body_b)
        except zlib.error:
            body_b = zlib.decompress(body_b, -zlib.MAX_WBITS)
    return body_b.decode("utf-8", "replace")

def ms():
    return int(time.time() * 1000)

def show(text):
    try:
        blob = json.loads(text)
    except ValueError:
        return text
    if not (isinstance(blob, dict) and {"iv", "ct", "salt"} <= blob.keys()):
        return text
    key = hashlib.pbkdf2_hmac("sha256", dk.encode(), base64.b64decode(blob["salt"]),
                              blob["iter"], blob["ks"] // 8)
    return AESCCM(key, tag_length=blob["ts"] // 8).decrypt(
        base64.b64decode(blob["iv"]), base64.b64decode(blob["ct"]), b"").decode()

csrf = re.search(r"csrf_token\s*=\s*'([^']+)'", req("GET", "/login.html", PAGE)).group(1)
print("csrf_token:", csrf)
ul = json.loads(req("GET", f"/data/user_lang.json?_={ms()}&csrf_token={csrf}", XHR))
enc = next(e["encryption_key"] for e in ul if "encryption_key" in e)
print("encryption_key:", enc)
salt = next(e["salt"] for e in ul if "salt" in e)
print("salt:", salt)
h1 = hmac.new(b"$1$SERCOMM$", PWD.encode(), hashlib.sha256).hexdigest()
print("First Hash:", h1)
login_pwd = hmac.new(enc.encode(), h1.encode(), hashlib.sha256).hexdigest()
print("Second Hash:", login_pwd)
form = urllib.parse.urlencode({"LoginName": USER, "LoginPWD": login_pwd})
print("Request Body:", form)
login_resp = req("POST", f"/data/login.json?_={ms()}&csrf_token={csrf}", POST, form)
print("Response Body:", show(login_resp.rstrip()))
dk = hashlib.pbkdf2_hmac("sha256", PWD.encode(), bytes.fromhex(salt), 1000, 16).hex()
print("dk:", dk)
print("Cookies:", COOKIES)
password = req("GET", f"/data/settings_password.json?_={ms()}&csrf_token={csrf}", XHR)
print("Encrypted Response:", password)
password_dec = show(password)
print("Decrypted Response:", password_dec)
pwd_b64 = next(e["pwd"] for e in json.loads(password_dec) if "pwd" in e)
print("Base64 Decoded Password:", base64.b64decode(pwd_b64).decode())
