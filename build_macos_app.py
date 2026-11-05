import os
import shutil
import subprocess
from pathlib import Path

def build_app():
    project_dir = Path(__file__).resolve().parent
    app_name = "LocalWhisper.app"
    build_dir = project_dir / ".build_tmp"
    build_app_path = build_dir / app_name
    applications_dir = Path.home() / "Applications"
    installed_app_path = applications_dir / app_name
    entitlements_file = project_dir / "entitlements.plist"

    print(f"[Build] Assembling Self-Contained Native macOS App: {app_name}...")

    # 1. Clean previous builds and any legacy bundle in project dir
    legacy_project_app = project_dir / app_name
    if legacy_project_app.exists():
        shutil.rmtree(legacy_project_app, ignore_errors=True)
    if build_dir.exists():
        shutil.rmtree(build_dir, ignore_errors=True)

    # 2. Directory structure
    contents_dir = build_app_path / "Contents"
    macos_dir = contents_dir / "MacOS"
    resources_dir = contents_dir / "Resources"
    macos_dir.mkdir(parents=True, exist_ok=True)
    resources_dir.mkdir(parents=True, exist_ok=True)

    # 3. Copy Icon
    icns_file = project_dir / "AppIcon.icns"
    if icns_file.exists():
        shutil.copy(icns_file, resources_dir / "AppIcon.icns")
        print("[Build] Bundled AppIcon.icns.")

    # 4. Write PkgInfo
    with open(contents_dir / "PkgInfo", "w") as f:
        f.write("APPL????")

    # 5. Write Info.plist
    info_plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>LocalWhisper</string>
    <key>CFBundleDisplayName</key>
    <string>LocalWhisper</string>
    <key>CFBundleIdentifier</key>
    <string>com.antigravity.localwhisper</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundleExecutable</key>
    <string>LocalWhisper</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>LSMinimumSystemVersion</key>
    <string>11.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSMicrophoneUsageDescription</key>
    <string>LocalWhisper needs access to your microphone to transcribe speech locally and completely offline.</string>
    <key>NSSpeechRecognitionUsageDescription</key>
    <string>LocalWhisper transcribes speech locally using offline Whisper AI.</string>
    <key>NSAccessibilityUsageDescription</key>
    <string>LocalWhisper uses accessibility features to type transcribed text directly into your active application.</string>
    <key>Privacy - Accessibility Usage Description</key>
    <string>LocalWhisper uses accessibility features to type transcribed text directly into your active application.</string>
    <key>LSUIElement</key>
    <false/>
</dict>
</plist>
"""
    with open(contents_dir / "Info.plist", "w") as f:
        f.write(info_plist_content)

    # 6. Compile Native Mach-O Launcher with Embedded Python
    launcher_src = project_dir / "launcher.m"
    binary_dest = macos_dir / "LocalWhisper"
    
    print("[Build] Compiling native Mach-O binary with embedded Python...")
    compile_cmd = [
        "clang",
        "-O2",
        "-arch", "arm64",
        f"-DPROJECT_DIR_DEF=\"{project_dir}\"",
        "-I/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/Headers",
        "-F/Library/Developer/CommandLineTools/Library/Frameworks",
        "-framework", "Python3",
        "-framework", "Foundation",
        "-framework", "AVFoundation",
        "-framework", "ApplicationServices",
        "-framework", "Cocoa",
        "-Wl,-rpath,/Library/Developer/CommandLineTools/Library/Frameworks",
        "-o", str(binary_dest),
        str(launcher_src)
    ]
    subprocess.run(compile_cmd, check=True)
    binary_dest.chmod(0o755)
    print(f"[Build] Compiled native executable: {binary_dest}")

    # 7. Code Sign with Permanent Designated Requirement and Entitlements
    print("[Build] Code-signing with permanent designated requirement...")
    sign_cmd = [
        "codesign",
        "-s", "-",
        "--force",
        "--deep",
        "--entitlements", str(entitlements_file),
        "-r=designated => identifier \"com.antigravity.localwhisper\"",
        str(build_app_path)
    ]
    subprocess.run(sign_cmd, check=True)

    # 8. Install into user ~/Applications
    applications_dir.mkdir(parents=True, exist_ok=True)
    if installed_app_path.exists():
        shutil.rmtree(installed_app_path, ignore_errors=True)
        if installed_app_path.exists():
            os.remove(installed_app_path)

    print(f"[Install] Installing to {installed_app_path}...")
    shutil.copytree(build_app_path, installed_app_path)

    # Clean up temporary build folder so only 1 copy exists on disk
    if build_dir.exists():
        shutil.rmtree(build_dir, ignore_errors=True)

    # Re-sign installed bundle to guarantee path integrity
    sign_installed_cmd = [
        "codesign",
        "-s", "-",
        "--force",
        "--deep",
        "--entitlements", str(entitlements_file),
        "-r=designated => identifier \"com.antigravity.localwhisper\"",
        str(installed_app_path)
    ]
    subprocess.run(sign_installed_cmd, check=True)

    # 9. Register with macOS LaunchServices
    lsregister_cmd = "/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"
    if os.path.exists(lsregister_cmd):
        try:
            subprocess.run([lsregister_cmd, "-f", str(installed_app_path)], check=True)
            print("[Install] Registered with macOS LaunchServices.")
        except Exception as e:
            print(f"[Install] Note: lsregister warning: {e}")

    subprocess.run(["touch", str(installed_app_path)])

    print(f"\n[SUCCESS] LocalWhisper whole-package native app built, signed with stable requirement, and installed!")
    print(f"Location: {installed_app_path}")

if __name__ == "__main__":
    build_app()
