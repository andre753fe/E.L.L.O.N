#!/usr/bin/env python3
"""Gera agenda.ics (calendário subscrito no iPhone/iPad) a partir de data/eventos.json e do plano de compras."""
import json, datetime as dt, hashlib, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOMES = {"O": "Realty Income", "VUAA": "S&P 500 (VUAA)", "VHYL": "Dividendos mundo (VHYL)", "USDV": "Dividend Aristocrats (USDV)",
         "BCP": "Millennium bcp", "WTRG": "Essential Utilities", "NVDA": "Nvidia", "NEE": "NextEra Energy", "CMCSA": "Comcast",
         "NNE": "NANO Nuclear", "SPCX": "SpaceX", "PPR": "PPR"}
TIPO = {"earnings": "Resultados", "ex": "Data ex-dividendo", "pay": "Pagamento de dividendo"}

def esc(s):
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

def fold(line):
    out, b = [], line.encode("utf-8")
    while len(b) > 74:
        cut = 74
        while (b[cut] & 0xC0) == 0x80: cut -= 1
        out.append(b[:cut].decode("utf-8")); b = b[cut:]
    out.append(b.decode("utf-8"))
    return "\r\n ".join(out)

def plano(hoje, meses=12):
    ev = []
    y, m = hoje.year, hoje.month
    for _ in range(meses):
        ym = y * 12 + (m - 1)
        antigo = ym < 2027 * 12
        d20 = dt.date(y, m, 20)
        quando = d20 + dt.timedelta(days={5: 2, 6: 1}.get(d20.weekday(), 0))
        itens = ["5 ações da Realty Income · Trading 212",
                 "1 unidade do S&P 500 (VUAA) · " + ("XTB, linha em dólares" if antigo else "Trading 212, Xetra, em euros")]
        if (ym - (2026 * 12 + 10)) % 2 == 0: itens.append("1 unidade de VHYL (≈82 €) · XTB, Euronext Amsterdam, em euros")
        if not antigo: itens.append("USDV: se os dividendos juntos na Trading 212 já chegarem ao preço, 1 unidade (Xetra, em euros)")
        nota = "" if quando == d20 else f"\nO dia 20 calha ao fim de semana: compra na segunda, dia {quando.day}."
        ev.append({"d": quando, "uid": f"compras-{y}-{m:02d}", "sum": "Compras do mês", "desc": "\n".join("• " + i for i in itens) + nota})
        ev.append({"d": dt.date(y, m, 5), "uid": f"ppr-{y}-{m:02d}", "sum": "PPR: débito automático de 25 €", "desc": "Optimize PPR Agressivo · automático."})
        m += 1
        if m > 12: m, y = 1, y + 1
    return [e for e in ev if e["d"] >= hoje]

def main():
    hoje = dt.datetime.now(dt.timezone.utc).date()
    doc = json.load(open(os.path.join(ROOT, "data", "eventos.json"), encoding="utf-8"))
    evs = []
    for e in doc.get("events", []):
        k = e.get("k")
        if k not in TIPO: continue
        d = dt.date.fromisoformat(e["d"])
        if d < hoje - dt.timedelta(days=30): continue
        t = e.get("t", "")
        desc = e.get("txt", "")
        src = (e.get("src") or {}).get("url")
        if src: desc += "\nFonte: " + src
        uid = "ev-" + hashlib.sha1(f'{e["d"]}|{t}|{k}'.encode()).hexdigest()[:16]
        evs.append({"d": d, "uid": uid, "sum": f"{TIPO[k]} · {NOMES.get(t, t)}", "desc": desc})
    evs += plano(hoje)
    evs.sort(key=lambda x: (x["d"], x["sum"]))
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    L = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//E.L.L.O.N//Agenda//PT", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
         "X-WR-CALNAME:E.L.L.O.N · Mercados", "X-WR-TIMEZONE:Europe/Lisbon", "REFRESH-INTERVAL;VALUE=DURATION:PT6H", "X-PUBLISHED-TTL:PT6H"]
    for e in evs:
        L += ["BEGIN:VEVENT", f"UID:{e['uid']}@ellon-nexus", f"DTSTAMP:{stamp}",
              f"DTSTART;VALUE=DATE:{e['d']:%Y%m%d}", f"DTEND;VALUE=DATE:{e['d'] + dt.timedelta(days=1):%Y%m%d}",
              "SUMMARY:" + esc(e["sum"]), "DESCRIPTION:" + esc(e["desc"]), "TRANSP:TRANSPARENT",
              "BEGIN:VALARM", "ACTION:DISPLAY", "DESCRIPTION:" + esc(e["sum"]), "TRIGGER:-PT15H", "END:VALARM", "END:VEVENT"]
    L.append("END:VCALENDAR")
    with open(os.path.join(ROOT, "agenda.ics"), "w", encoding="utf-8", newline="") as f:
        f.write("\r\n".join(fold(x) for x in L) + "\r\n")
    print(len(evs), "eventos")

if __name__ == "__main__":
    main()
