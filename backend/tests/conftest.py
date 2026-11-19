"""
Configuration pytest partagée. Ajoute la racine du backend au path une
seule fois ici, plutôt que dans chaque fichier de test (Phases 9-21
faisaient toutes sys.path.insert individuellement — fonctionnel mais
redondant).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
