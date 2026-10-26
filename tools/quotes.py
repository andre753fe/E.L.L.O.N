#!/usr/bin/env python3
"""Atualiza data/quotes.json (cotações do site público) a partir do Yahoo Finance.
Só mexe num ativo se a cotação vier válida e não mudar mais de 25% face ao valor guardado."""
import json, os, urllib.request, datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "data", "quotes.json")
SYMS = {"VUAA": ("VUAA.L", "USD"), "O": ("O", "USD"), "NEE": ("NEE", "USD"), "CMCSA": ("CMCSA", "USD"), "NVDA": ("NVDA", "USD"),
        "WTRG": ("WTRG", "USD"), "NNE": ("NNE", "USD"), "SPCX": ("SPCX", "USD"), "BCP": ("BCP.LS", "EUR")}

def chart(sym):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=1d&interval=15m"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (ellon-nexus quotes)"})
    with urllib.request.urlopen(req, timeout=20) as r:
        m = json.load(r)["chart"]["result"][0]["meta"]
    return float(m["regularMarketPrice"]), float(m.get("chartPreviousClose") or m.get("previousClose")), int(m.get("regularMarketTime") or 0)

def main():
    doc = json.load(open(PATH, encoding="utf-8"))
    prices, ok, fail, latest = doc.get("prices", {}), [], [], 0
    for t, (sym, cur) in SYMS.items():
        try:
            p, prev, ts = chart(sym)
            old = (prices.get(t) or {}).get("p")
            if p <= 0 or prev <= 0 or (old and abs(p / old - 1) > .25): raise ValueError("valor fora do esperado")
            prices[t] = {"cur": cur, "p": round(p, 4), "prev": round(prev, 4)}; ok.append(t); latest = max(latest, ts)
        except Exception as e:
            fail.append(f"{t} ({e.__class__.__name__})")
    try:
        fx, _, _ = chart("EURUSD=X")
        if .9 < fx < 1.4: doc["fx"] = round(fx, 4)
    except Exception:
        fail.append("EURUSD")
    if ok:
        doc["prices"] = dict(sorted(prices.items()))
        doc["asOf"] = dt.datetime.fromtimestamp(latest, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        doc["source"] = "Yahoo Finance (atualização automática do site)"
        with open(PATH, "w", encoding="utf-8") as f: json.dump(doc, f, ensure_ascii=False, indent=1); f.write("\n")
    print("atualizados:", ", ".join(ok) or "nenhum", "| falharam:", ", ".join(fail) or "nenhum")

if __name__ == "__main__":
    main()
