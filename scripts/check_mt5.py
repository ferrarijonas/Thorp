"""Health check para o watchdog — verifica se o terminal MT5 esta conectado ao broker.
Uso: python scripts/check_mt5.py <caminho_terminal>

Return codes:
  0 = MT5 conectado e pronto
  1 = MT5 nao conectado (processo ausente ou nao logado)
  2 = Erro (pacote ausente, etc.)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import MetaTrader5 as mt5
except ImportError:
    print("CHECK_MT5: MetaTrader5 nao instalado")
    sys.exit(2)

if len(sys.argv) < 2:
    print("CHECK_MT5: uso: python check_mt5.py <caminho_terminal>")
    sys.exit(2)

terminal_path = sys.argv[1]

if not os.path.exists(terminal_path):
    print("CHECK_MT5: terminal nao encontrado no caminho")
    sys.exit(1)

ok = mt5.initialize(path=terminal_path)
if not ok:
    print("CHECK_MT5: mt5.initialize() falhou")
    sys.exit(1)

try:
    info = mt5.terminal_info()
    if info is None:
        print("CHECK_MT5: terminal_info() retornou None")
        sys.exit(1)
    if not info.connected:
        print(f"CHECK_MT5: terminal desconectado (servidor: {info.server}, construcao: {info.build})")
        sys.exit(1)
    account = mt5.account_info()
    if account is None:
        print("CHECK_MT5: account_info() retornou None (nao logado)")
        sys.exit(1)
    print(f"CHECK_MT5: READY | server={info.server} build={info.build} login={account.login}")
    sys.exit(0)
finally:
    mt5.shutdown()
