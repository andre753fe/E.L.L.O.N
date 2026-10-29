"""Cotações de fecho, sem chave nem Claude: Yahoo Finance (gráfico diário) com reserva no Stooq.
Grava data/quotes.json = {asOf, fx, prices:{T:{p,prev,cur}}, watch:{...}, source}. Só dados públicos."""
import csv, io, json, os, sys, time, urllib.request
from datetime import datetime, timezone

ASSETS = {  # ticker do E.L.L.O.N: (Yahoo, Stooq, moeda)
    "VUAA": ("VUAA.L", "vuaa.uk", "USD"), "O": ("O", "o.us", "USD"), "NEE": ("NEE", "nee.us", "USD"),
    "CMCSA": ("CMCSA", "cmcsa.us", "USD"), "NVDA": ("NVDA", "nvda.us", "USD"), "WTRG": ("WTRG", "wtrg.us", "USD"),
    "NNE": ("NNE", "nne.us", "USD"), "SPCX": ("SPCX", "spcx.us", "USD"), "BCP": ("BCP.LS", "bcp.pt", "EUR"),
}
WATCH = {"CNQ": ("CNQ", "cnq.us", "USD")}
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}

def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
        return r.read().decode("utf-8", "replace")

def yahoo(sym):
    j = json.loads(get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=10d&interval=1d"))
    res = j["chart"]["result"][0]
    ts, closes = res["timestamp"], res["indicators"]["quote"][0]["close"]
    rows = [(t, c) for t, c in zip(ts, closes) if c is not None]
    meta = res["meta"]
    p = meta.get("regularMarketPrice") or rows[-1][1]
    # fecho anterior = penúltimo fecho diário (o último é o do dia do preço)
    prev = rows[-2][1] if len(rows) > 1 else meta.get("chartPreviousClose")
    when = datetime.fromtimestamp(meta.get("regularMarketTime") or rows[-1][0], timezone.utc)
    return round(float(p), 4), round(float(prev), 4), when, meta.get("currency")

def stooq(sym):
    rows = list(csv.DictReader(io.StringIO(get(f"https://stooq.com/q/d/l/?s={sym}&i=d"))))
    rows = [r for r in rows if r.get("Close") not in (None, "", "N/D")]
    a, b = rows[-1], rows[-2]
    when = datetime.strptime(a["Date"], "%Y-%m-%d").replace(hour=21, tzinfo=timezone.utc)
    return round(float(a["Close"]), 4), round(float(b["Close"]), 4), when, None

def fetch(ys, ss):
    for fn, s in ((yahoo, ys), (stooq, ss)):
        try:
            return fn(s) + (fn.__name__,)
        except Exception as e:
            print("falhou", fn.__name__, s, e, file=sys.stderr)
        time.sleep(1)
    return None

path = "data/quotes.json"
old = json.load(open(path)) if os.path.exists(path) else {"prices": {}, "watch": {}}
out = {"prices": dict(old.get("prices", {})), "watch": dict(old.get("watch", {})), "fx": old.get("fx")}
latest, used, failed = None, set(), []
for group, table in (("prices", ASSETS), ("watch", WATCH)):
    for t, (ys, ss, cur) in table.items():
        r = fetch(ys, ss)
        if not r:
            failed.append(t); continue
        p, prev, when, ycur = r[0], r[1], r[2], r[3]
        oldp = (old.get(group, {}).get(t) or {}).get("p")
        if oldp and abs(p / oldp - 1) > 0.35:  # salto absurdo: mantém o que estava
            failed.append(t); continue
        if ycur == "GBp":  # cotado em pence
            p, prev, cur = p / 100, prev / 100, "GBP"
        out[group][t] = {"p": p, "prev": prev, "cur": cur}
        used.add(r[4]); latest = max(latest or when, when)
fx = fetch("EURUSD=X", "eurusd")
if fx and 0.9 < fx[0] < 1.4:
    out["fx"] = fx[0]; used.add(fx[4])
out["asOf"] = (latest or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
out["source"] = "Fecho diário via " + " e ".join(sorted("Yahoo Finance" if u == "yahoo" else "Stooq" for u in used)) + (f"; sem dados: {', '.join(failed)}" if failed else "")
json.dump(out, open(path, "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False))
