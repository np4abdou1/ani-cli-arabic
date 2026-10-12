# ani-cli-arabic Roadmap

Future milestones and distribution plans for ani-cli-arabic.

---

## 1. User Profiles & Sync
* **Watch History & Favorites Sync**:
  - Optional cloud backup for watch history and bookmarks.
  - Multi-device continuity between machines.

---

## 2. Universal Packaging & Distribution
Automate package publishing for common package managers:

* **Windows**:
  - **WinGet**: Manifest automation.
  - **Scoop**: Scoop bucket integration.
* **Linux**:
  - **Arch Linux**: AUR package (`ani-cli-arabic` & `ani-cli-arabic-git`).
  - **Ubuntu / Debian**: `.deb` packaging.
  - **AppImage**: Standalone bundle.
* **Python**:
  - **PyPI**: Automated workflow on release tags.

---

## 3. Release Pipeline
* Release workflow for tagged builds:
  1. Build wheel & sdist for PyPI.
  2. Generate SHA256 checksums.
  3. Publish release artifacts.
