import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.app import AniCliArApp
from src.version import APP_VERSION
from src.utils import is_bundled
from src.updater import check_for_updates

if __name__ == "__main__":
    # check for updates only when running as compiled exe
    if is_bundled():
        check_for_updates()
    
    app = AniCliArApp()
    app.run()
