import os
import sys
import subprocess
import shutil
import platform
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

def download_mpv_instructions():
    system = platform.system()
    
    print("\n" + "⚠"*30)
    print("\n  MPV NOT FOUND!")
    print("\n  MPV is required to play anime videos.")
    print("\n" + "⚠"*30 + "\n")
    
    if system == "Windows":
        print("📥 Download MPV for Windows:")
        print("   1. Visit: https://mpv.io/installation/")
        print("   2. Download the Windows build")
        print("   3. Extract mpv.exe to your PATH or project folder")
        print("   4. Or place mpv.exe in: scripts/mpv/mpv.exe")
    elif system == "Darwin":  # macOS
        print("📥 Install MPV on macOS:")
        print("   Run: brew install mpv")
    elif system == "Linux":
        print("📥 Install MPV on Linux:")
        print("   Ubuntu/Debian: sudo apt install mpv")
        print("   Fedora: sudo dnf install mpv")
        print("   Arch: sudo pacman -S mpv")
    
    print("\n" + "-"*60)
    response = input("\nDo you want to continue building WITHOUT MPV? (y/n): ").strip().lower()
    return response == 'y'

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

def build_executable(bundle_mpv=False):
    system = platform.system()
    script_dir = Path(__file__).parent.parent
    main_file = script_dir / "main.py"
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
    
    cmd = [
        'pyinstaller',
        '--onefile',
        '--name', 'ani-cli-ar',
        '--console',
        '--clean',
        '--noconfirm',
        '--distpath', str(script_dir),
        '--workpath', str(build_dir),
        '--specpath', str(build_dir),
    ]
    
    if icon_path.exists() and system == "Windows":
        print(f"🎨 Icon: {icon_path}")
        cmd.extend(['--icon', str(icon_path)])
    elif system == "Windows":
        print("⚠ No icon found (optional)")
    
    cmd.extend([
        '--add-data', f'{script_dir / "src"}{os.pathsep}src',
        '--add-data', f'{script_dir / "themes.py"}{os.pathsep}.',
        '--add-data', f'{script_dir / "database"}{os.pathsep}database',
        '--hidden-import', 'pypresence',
        '--hidden-import', 'rich',
        '--hidden-import', 'requests',
        '--hidden-import', 'cryptography',
        '--hidden-import', 'cryptography.fernet',
    ])
    
    if bundle_mpv:
        mpv_path = find_mpv_executable()
        if mpv_path and mpv_path.exists():
            cmd.extend(['--add-binary', f'{mpv_path}{os.pathsep}mpv'])
    
    cmd.append(str(main_file))
    
    print("\n🔨 Building...")
    print("   [1/5] Analyzing dependencies...")
    
    try:
        process = subprocess.Popen(
            cmd, 
            cwd=script_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        stage = 1
        for line in process.stdout:
            line = line.strip()
            
            if "Analyzing" in line and stage == 1:
                print("   [2/5] Building module graph...")
                stage = 2
            elif "Building PYZ" in line and stage == 2:
                print("   [3/5] Compiling Python modules...")
                stage = 3
            elif "Building PKG" in line and stage == 3:
                print("   [4/5] Packaging resources...")
                stage = 4
            elif ("Building EXE" in line or "Building BUNDLE" in line) and stage == 4:
                print("   [5/5] Creating executable...")
                stage = 5
            elif "WARNING" in line or "ERROR" in line:
                print(f"   ⚠️  {line}")
        
        process.wait()
        
        if process.returncode != 0:
            print("\n✗ Build failed with errors")
            return False
        
        if system == "Windows":
            exe_name = "ani-cli-ar.exe"
        elif system == "Darwin":
            exe_name = "ani-cli-ar"
        else:
            exe_name = "ani-cli-ar"
        
        exe_path = script_dir / exe_name
        
        if exe_path.exists():
            print(f"\n✓ Build successful!")
            print(f"📦 Executable: {exe_path}")
            print(f"📊 Size: {exe_path.stat().st_size / 1024 / 1024:.2f} MB")
            print(f"📁 Build files: {build_dir}")
            return True
        
        print("✗ Build failed: Executable not found")
        return False
        
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Build failed with error code {e.returncode}")
        return False
    except Exception as e:
        print(f"\n✗ Build failed: {e}")
        return False

def main():
    print_header("ani-cli-ar Build Tool")
    
    print("🔍 Checking system requirements...\n")
    
    mpv_installed = check_mpv_installed()
    if mpv_installed:
        print("✓ MPV found")
    else:
        print("✗ MPV not found")
        if not download_mpv_instructions():
            print("\n❌ Build cancelled by user")
            return 1
    
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
        
        if not mpv_installed:
            print("\n⚠ Remember: MPV is not installed!")
            print("  The app will not play videos without MPV.")
        
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
