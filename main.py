import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.app import AniCliArApp
from src.config import CURRENT_VERSION
from src.utils import is_bundled

if __name__ == "__main__":
    app = AniCliArApp()
    app.run()
