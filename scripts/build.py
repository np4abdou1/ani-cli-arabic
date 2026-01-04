import os
import sys
import subprocess
import shutil
import platform
import threading
import time
from pathlib import Path

def print_header(text):
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60 + "\n")

def check_mpv_installed():
    try:
        result = subprocess.run(
            ['mpv', '--version'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

def check_pyinstaller():
    try:
        import PyInstaller
        return True
    except ImportError:
        return False

def install_pyinstaller():
    print("Installing PyInstaller...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])
        print("✓ PyInstaller installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("✗ Failed to install PyInstaller")
        return False

def find_mpv_executable():
    try:
        result = subprocess.run(
            ['where' if platform.system() == 'Windows' else 'which', 'mpv'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0:
            mpv_path = result.stdout.strip().split('\n')[0]
            return Path(mpv_path) if mpv_path else None
    except Exception:
        pass
    return None

def create_spec_file(script_dir, bundle_mpv=False):
    """Create a .spec file for PyInstaller with optimized settings."""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path

block_cipher = None
script_dir = Path(r"{script_dir}")

a = Analysis(
    ['main.py'],
    pathex=[str(script_dir)],
    binaries={binaries},
    datas=[
        (str(script_dir / 'src'), 'src'),
    ],
    hiddenimports=[
        'pypresence',
        'rich',
        'rich.console',
        'rich.panel',
        'rich.text',
        'rich.prompt',
        'rich.progress',
        'rich.align',
        'rich.box',
        'rich.table',
        'requests',
        'cryptography',
        'cryptography.fernet',
        'src.version',
        'src.updater',
        'src.config',
        'src.app',
        'src.api',
        'src.player',
        'src.discord_rpc',
        'src.models',
        'src.ui',
        'src.utils',
        'src.history',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=['IPython', 'jupyter', 'notebook', 'matplotlib', 'scipy', 'pandas', 'numpy', 'tkinter'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ani-cli-ar',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(script_dir / 'assets' / 'icon.ico') if (script_dir / 'assets' / 'icon.ico').exists() else None,
)
'''
    
    binaries = "[]"
    if bundle_mpv:
        mpv_path = find_mpv_executable()
        if mpv_path and mpv_path.exists():
            binaries = f"[(r'{mpv_path}', 'mpv')]"
    
    spec_content = spec_content.format(script_dir=str(script_dir), binaries=binaries)
    
    spec_file = Path(__file__).parent / "ani-cli-ar.spec"
    with open(spec_file, 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    return spec_file

def build_executable(bundle_mpv=False):
    system = platform.system()
    script_dir = Path(__file__).parent.parent
    main_file = script_dir / "main.py"
    dist_dir = script_dir / "dist"
    build_dir = script_dir / "build"
    
    if not main_file.exists():
        print(f"✗ Error: {main_file} not found")
        return False
    
    print_header("Building Executable")
    print(f"📦 System: {system}")
    print(f"🐍 Python: {sys.version.split()[0]}")
    print(f"📂 Script: {main_file}")
    
    if bundle_mpv:
        mpv_path = find_mpv_executable()
        if mpv_path and mpv_path.exists():
            print(f"📹 MPV: {mpv_path} (will be bundled)")
        else:
            print("⚠️  MPV: Not found in PATH, skipping bundle")
            bundle_mpv = False
    else:
        print("📹 MPV: User will need to install separately")
    
    icon_path = script_dir / "assets" / "icon.ico"
    if icon_path.exists() and system == "Windows":
        print(f"🎨 Icon: {icon_path}")
    elif system == "Windows":
        print("⚠ No icon found (optional)")
    
    # Create optimized spec file
    print("\n🔧 Generating build configuration...")
    spec_file = create_spec_file(script_dir, bundle_mpv)
    print(f"✓ Created: {spec_file}")
    
    print("\n🔨 Building executable...")
    print("   This typically takes 2-5 minutes\n")
    
    # Build stages based on actual PyInstaller output
    stages = {
        0: "Initializing",
        1: "Analyzing dependencies", 
        2: "Building module graph",
        3: "Processing hooks",
        4: "Building PYZ archive",
        5: "Building PKG archive",
        6: "Building executable",
        7: "Finalizing"
    }
    
    current_stage = [0]
    stage_progress = [0.0]
    build_complete = threading.Event()
    build_success = [False]
    
    def run_build():
        try:
            cmd = [sys.executable, '-m', 'PyInstaller', '--clean', '--noconfirm', str(spec_file)]
            process = subprocess.Popen(
                cmd,
                cwd=script_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            for line in process.stdout:
                line = line.strip()
                
                # detect stages from PyInstaller output
                if 'PyInstaller:' in line:
                    current_stage[0] = 0
                elif 'Analyzing' in line or 'Looking for' in line:
                    current_stage[0] = max(current_stage[0], 1)
                elif 'Initializing module' in line or 'module dependency graph' in line:
                    current_stage[0] = max(current_stage[0], 2)
                elif 'Processing' in line and 'hook' in line:
                    current_stage[0] = max(current_stage[0], 3)
                elif 'Building PYZ' in line:
                    current_stage[0] = max(current_stage[0], 4)
                elif 'Building PKG' in line:
                    current_stage[0] = max(current_stage[0], 5)
                elif 'Building EXE' in line or 'Building BUNDLE' in line:
                    current_stage[0] = max(current_stage[0], 6)
                elif 'completed successfully' in line:
                    current_stage[0] = 7
            
            process.wait()
            build_success[0] = (process.returncode == 0)
        except Exception as e:
            build_success[0] = False
        finally:
            current_stage[0] = 7
            build_complete.set()
    
    build_thread = threading.Thread(target=run_build, daemon=True)
    build_thread.start()
    
    # Show progress bar
    start_time = time.time()
    bar_width = 40
    last_stage = -1
    
    while not build_complete.is_set():
        elapsed = time.time() - start_time
        stage = current_stage[0]
        
        # calculate progress (each stage is weighted)
        stage_weights = {0: 5, 1: 15, 2: 20, 3: 15, 4: 15, 5: 15, 6: 10, 7: 5}
        total_weight = sum(stage_weights.values())
        completed_weight = sum(stage_weights[i] for i in range(stage))
        
        # add partial progress within current stage based on time spent in it
        if stage < 7:
            if stage != last_stage:
                last_stage = stage
                stage_start_time = time.time()
            
            time_in_stage = time.time() - stage_start_time
            # estimate 10 seconds per stage for smoother progress
            stage_completion = min(0.9, time_in_stage / 10.0)
            current_weight = stage_weights[stage] * stage_completion
        else:
            current_weight = stage_weights.get(7, 0)
        
        overall_progress = (completed_weight + current_weight) / total_weight
        
        # calculate ETA
        if elapsed > 3 and overall_progress > 0.1:
            estimated_total = elapsed / overall_progress
            eta_seconds = max(0, estimated_total - elapsed)
            eta_minutes = int(eta_seconds // 60)
            eta_secs = int(eta_seconds % 60)
            eta_str = f"{eta_minutes}m {eta_secs}s" if eta_minutes > 0 else f"{eta_secs}s"
        else:
            eta_str = "calculating..."
        
        # draw progress bar
        filled = int(bar_width * overall_progress)
        bar = '█' * filled + '░' * (bar_width - filled)
        percentage = int(overall_progress * 100)
        
        stage_name = stages.get(stage, "Processing")
        
        # clear line and print progress
        sys.stdout.write('\r')
        sys.stdout.write(f"   [{bar}] {percentage:>3}% | {stage_name:<30} | ETA: {eta_str:<12}")
        sys.stdout.flush()
        
        time.sleep(0.3)
    
    # final progress
    sys.stdout.write('\r')
    sys.stdout.write(f"   [{'█' * bar_width}] 100% | Build complete{' ' * 30} | Done!{' ' * 12}\n")
    sys.stdout.flush()
    
    if not build_success[0]:
        print("\n✗ Build failed. Check PyInstaller output for errors.")
        return False
    
    # Find the executable
    if system == "Windows":
        exe_name = "ani-cli-ar.exe"
    else:
        exe_name = "ani-cli-ar"
    
    exe_path = dist_dir / exe_name
    
    if exe_path.exists():
        print(f"\n✓ Build successful!")
        print(f"📦 Executable: {exe_path}")
        print(f"📊 Size: {exe_path.stat().st_size / 1024 / 1024:.2f} MB")
        
        # Clean up spec file
        if spec_file.exists():
            spec_file.unlink()
            print(f"🧹 Cleaned up: {spec_file.name}")
        
        return True
    
    print("✗ Build failed: Executable not found")
    return False

def main():
    print_header("ani-cli-arabic Build Tool")
    
    # Check PyInstaller
    if not check_pyinstaller():
        print("⚠ PyInstaller not found")
        if not install_pyinstaller():
            print("\n❌ Cannot continue without PyInstaller")
            return 1
        print()
    
    print("🔍 Checking system requirements...\n")
    
    mpv_installed = check_mpv_installed()
    if mpv_installed:
        print("✓ MPV found")
    else:
        print("⚠ MPV not found (optional for bundling)")
    
    bundle_mpv = False
    if mpv_installed:
        print("\n" + "-"*60)
        system = platform.system()
        mpv_name = "MPV.exe" if system == "Windows" else "MPV"
        mpv_response = input(f"\n📹 Bundle {mpv_name} with the executable? (y/n): ").strip().lower()
        bundle_mpv = (mpv_response == 'y')
        
        if bundle_mpv:
            print("✓ MPV will be bundled (larger file size, but no MPV installation needed)")
        else:
            print("✓ MPV will NOT be bundled (users need to install MPV separately)")
    
    print("\n" + "-"*60)
    response = input("\nProceed with build? (y/n): ").strip().lower()
    
    if response != 'y':
        print("\n❌ Build cancelled")
        return 0
    
    if build_executable(bundle_mpv):
        print("\n" + "="*60)
        print("  🎉 BUILD COMPLETE!")
        print("="*60)
        
        if not bundle_mpv:
            print("\n⚠ Note: MPV is NOT bundled in the executable.")
            print("  Users will need MPV installed to play videos.")
        
        return 0
    else:
        print("\n" + "="*60)
        print("  ❌ BUILD FAILED")
        print("="*60)
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n❌ Build interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        sys.exit(1)
