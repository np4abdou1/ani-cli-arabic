import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.app import main
from src.utils import is_bundled
from src.updater import check_for_updates

if __name__ == "__main__":
    if is_bundled():
        check_for_updates()
    
    main()
