"""Demo ao vivo — H141 (Continuacao de 9:00).
Uso: python scripts/run_demo.py [--terminal xp]
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.run_bot import main as bot_main

if __name__ == "__main__":
    terminal = "xp"
    if len(sys.argv) > 1 and sys.argv[1] == "--terminal" and len(sys.argv) > 2:
        terminal = sys.argv[2]
    sys.argv = [sys.argv[0], "--terminal", terminal]
    bot_main()
