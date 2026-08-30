# 🗺️ ani-cli-arabic Roadmap & Future Architecture

This document tracks upcoming architectural features, multi-platform distribution packages, and AI agent integrations planned for future major releases.

---

## 1. 👤 User Profiles & Cloud Synchronization
* **Cloud Watch History & Favorites**:
  - Secure remote synchronization of watch history, bookmarks, and settings.
  - Multi-device continuity (e.g. resume on laptop where you left off on desktop).
* **Authentication Options**:
  - Google OAuth2 single-sign-on (SSO) via device code flow.
  - Standard username/password registration with end-to-end token encryption.

---

## 2. 🤖 AI Anime Companion Mode
* **Terminal AI Agent**:
  - Conversational AI assistant built directly into the CLI.
  - Model provider integration powered by **OpenCode Zen API**.
* **Capabilities**:
  - Live real-time anime web search and lore lookups.
  - Personalized recommendation engine based on watch history.
  - Autonomous task execution (e.g., finding filler episode guides, finding seasonal schedules, automated batch queues).

---

## 3. 📦 Universal Multi-Platform Distribution & Packaging
Automate automated CI/CD GitHub Actions workflows to build, test, and publish packages across all major ecosystems:

* **Windows**:
  - **WinGet**: Microsoft Community Repository manifest automation.
  - **Scoop**: Scoop bucket integration and auto-updating manifests.
* **Linux Distributions**:
  - **Arch Linux**: Automated AUR package (`ani-cli-arabic` & `ani-cli-arabic-git`) publishing via SSH deploy keys.
  - **Ubuntu / Debian**: Launchpad PPA repository and `.deb` packaging.
  - **Fedora / RHEL**: Copr build repository and `.rpm` specs.
  - **Snapcraft**: Snap store automated publishing.
* **Python Ecosystem**:
  - **PyPI**: Automated Trusted Publisher workflow for tag releases.
* **Universal Binaries**:
  - Self-contained single-binary AppImages and standalone releases.

---

## 4. 🚀 CI/CD Release Automation
* GitHub Actions release workflow triggering multi-target builds upon new version tags:
  1. Build wheel & sdist $\rightarrow$ Publish to PyPI.
  2. Generate SHA256 hashes $\rightarrow$ Update WinGet & Scoop PRs.
  3. Push PKGBUILD $\rightarrow$ Update AUR repository.
  4. Generate release notes from `src/changelog.py`.
