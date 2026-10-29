# Changelog

All notable changes to **ani-cli-arabic** are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.1.0] - 2026-10-29

### Added
- **Stardima Providers (`stardima` & `stardima_kids`)**:
  - Full support for Arabic-dubbed anime and Arabic-dubbed cartoons.
  - Multi-server extraction pipeline supporting direct `backup` streams, `Uqload`, `Mixdrop`, `LuluStream`, `SaveFiles`, `Mp4upload`, `Forafile`, and `Firestream`.
  - Automatic audio track selection choosing Arabic audio (`ara`, `ar`) for dubbed streams.
  - Pre-indexed TMDB classification database to cleanly separate anime from cartoon/kids titles without runtime network latency.
  - Settings support for Stardima audio preference (`dub`, `sub`, `both`).
- **Dynamic Main Screen Keybind Hints**:
  - Main menu action hints (`(e, m, t, p, r, g, s)`) and search bar hints adapt dynamically to each provider's capabilities.
  - Interactive mouse grid hitboxes recalculate dynamically based on available provider shortcuts.
- **Settings Navigation**:
  - `Tab` and `Shift+Tab` support to cycle between settings tabs smoothly.
  - Instant setting reloads so provider and playback preferences update without restarting the application.

### Fixed
- **MPV Header Normalization**: Hardened HTTP header formatting for video players, escaping newlines and colons to prevent `HTTP 400 Bad Request` errors on CDN streams.
- **Keybind Dispatch Guards**: Guarded single-key shortcut dispatch against invoking unsupported features on providers that do not index them.
- **Livewire Sanity Tests**: Made CI live sanity tests graceful against temporary Cloudflare challenge blocks.

---

## [2.0.1] - 2026-10-15

### Fixed
- **UI Rendering**: Fixed batch selection menu where non-cursor episode rows were hidden.
- **Range Parsing**: Correctly bound episode ranges by the highest available episode number instead of episode count, allowing seasons starting past episode 1 to be downloaded in batch.
- **Just-in-Time Link Resolution**: Stream URLs are now resolved right before each episode starts downloading, preventing signed CDN tokens from expiring during multi-episode batches.
- **Rate-Limiting Protection**: Link resolutions are serialized through a lock so scraping requests don't trigger Cloudflare rate-limits, while file downloads continue in parallel.
- **Provider Headers**: Forwarded required HTTP headers (such as `Referer`) to download requests to prevent 403 Forbidden CDN rejections.
- **Skip Existing Files**: Episodes already complete on disk are skipped before making unnecessary scraping requests.
- **HLS Protection**: Rejects unsupported `.m3u8` streams with a clear warning instead of saving corrupt plaintext files as `.mp4`.
- **Cancellation & Summary**: Responsive `Ctrl+C` handling across all operating systems and clear summary listing of any failed episodes.

---

## [2.0.0] - 2026-10-15

### Added
- **Complete Architectural Overhaul**: Instant startup, zero terminal lag, smooth scrolling, and optimized memory usage.
- **HiAnime Integration**: Upgraded streaming engine with dynamic stream referer resolution, high-speed CDNs, and English Sub/Dub support.
- **Native Batch Downloader**: Built-in multithreaded chunked downloader with auto-resume, parallel speed, and zero external CLI dependencies.
- **Native FZF CLI Mode**: Completely rewritten interactive mode (`-i`) with native fzf, mouse navigation, no Arabic RTL glitches, and episode action menus.
- **Universal Player Support**: Seamless integration with MPV, VLC, Celluloid, IINA, and Syncplay with real-time JSON-IPC exact-second resume.
- **Zero-Downtime Infrastructure**: Resilient 3-tier domain fallback chains across custom domains, Cloudflare Pages, and Cloudflare Workers.
- **Privacy Hardening**: Removed playback tracking and isolated development builds from telemetry.
- **Cross-Platform Auto-Updater**: Instant automated updates across PyPI (`pip`), Arch Linux (`yay` / `paru`), and Homebrew.
