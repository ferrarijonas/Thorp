import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core import data
from importlib.util import spec_from_file_location, module_from_spec

def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/test_hipotese.py <HID>")
        sys.exit(1)

    hid = sys.argv[1].upper()
    candidates = [d for d in os.listdir("hipoteses") if d.startswith(hid)]
    if not candidates:
        print(f"Erro: {hid}* nao encontrada em hipoteses/")
        sys.exit(1)
    pasta = os.path.join("hipoteses", candidates[0])

    with open(os.path.join(pasta, "dados.json"), encoding="utf-8-sig") as f:
        params = json.load(f)

    logic_path = os.path.join(pasta, "logic.py")
    if not os.path.isfile(logic_path):
        print(f"Erro: {logic_path} nao encontrado")
        sys.exit(1)

    spec = spec_from_file_location("logic", logic_path)
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)

    df = data.load_csv()

    print(f"\n=== {hid} - {params.get('nome','?')} ===")
    resultado = mod.run(df, params)

    with open(os.path.join(pasta, "dados.json"), "w", encoding="utf-8") as f:
        params["status"] = resultado["status"]
        params["data_teste"] = "2026-05-17"
        params["resultado"] = {k: v for k, v in resultado.items() if k != "status"}
        json.dump(params, f, indent=2, ensure_ascii=False)

    print(f"Trades: {resultado['trades']}  | Media: {resultado['media_pts']:+.0f} pts  | WR: {resultado['wr_pct']:.0f}%")
    print(f"PF: {resultado['pf']:.2f}  | p: {resultado['p_valor']:.4f}")
    print(f"Metades: {resultado['metade1_media']:+.0f} / {resultado['metade2_media']:+.0f} -> {'OK' if resultado.get('metades_ok') else 'DIVERGE'}")
    print(f"STATUS: {resultado['status']}")

    with open("state/decisions.log", "a", encoding="utf-8") as f:
        from datetime import datetime
        f.write(f"{datetime.now():%Y-%m-%d %H:%M} | {hid} testado | p={resultado['p_valor']:.4f} WR={resultado['wr_pct']:.0f}% media={resultado['media_pts']:+.0f}pts -> {resultado['status']}\n")

if __name__ == "__main__":
    main()
