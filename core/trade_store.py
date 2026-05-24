"""Re-export do core/persistence.py para compatibilidade com código legado.
Novo código deve importar direto de core.persistence:
  from core.persistence import TradeStore, CapitalStore
"""
from core.persistence import TradeStore, CapitalStore
