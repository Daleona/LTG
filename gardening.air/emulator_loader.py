import csv
from pathlib import Path

def get_active_emulators(csv_path: str | Path = "Emu.csv") -> list[str]:
    """
    Liest Emu.csv und gibt eine Liste der Emulator-Adressen zurück,
    bei denen das Flag 'x' gesetzt ist.

    Erkennt das Trennzeichen automatisch und ignoriert leere Zeilen.
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV-Datei nicht gefunden: {csv_path}")

    with open(csv_path, "r", encoding="utf-8") as f:
        sample = f.read(1024)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters="\t;,")
        except csv.Error:
            # Fallback, wenn Erkennung fehlschlägt
            dialect = csv.excel
            dialect.delimiter = ","

        reader = csv.DictReader(f, dialect=dialect)

        active_addrs = []
        for row in reader:
            if not row:
                continue  # leere Zeilen überspringen

            flag = str(row.get("Flag", "")).strip().lower()
            if flag == "x":
                addr = str(row.get("Emu-Adress", "")).strip()
                if addr:
                    active_addrs.append(addr)

    return active_addrs


# Nur zu Testzwecken (direkt ausführbar)
if __name__ == "__main__":
    try:
        addrs = get_active_emulators()
        if addrs:
            print("✅ Aktive Emulatoren gefunden:")
            for a in addrs:
                print("   -", a)
        else:
            print("⚠️  Keine aktiven Emulatoren mit Flag 'x' gefunden.")
    except Exception as e:
        print("❌ Fehler:", e)

""" Use:
from emulator_loader import get_active_emulators

DEVICE_ADDRS = get_active_emulators()

for addr in DEVICE_ADDRS:
    print(f"Starte Prozess auf Emulator: {addr}")


or just for the first emulator in list:
DEVICE_ADDR = get_active_emulators()[0]

"""