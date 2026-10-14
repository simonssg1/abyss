#!/usr/bin/env bash
# Construit ~/Applications/Abyss.app (lanceur natif) + un alias « Abyss » sur le Bureau.
# Relançable sans effet de bord : l'ancienne app est remplacée proprement.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UV_BIN="$(command -v uv || true)"
if [[ -z "$UV_BIN" ]]; then
  echo "uv introuvable : installe-le (brew install uv) puis relance ce script." >&2
  exit 1
fi
UV_BIN="$(cd "$(dirname "$UV_BIN")" && pwd -P)/$(basename "$UV_BIN")"   # chemin absolu résolu au build
APP_DIR="$HOME/Applications"
APP="$APP_DIR/Abyss.app"
VERSION="$("$UV_BIN" run --project "$REPO" --quiet python -c 'import abyss; print(abyss.__version__)')"

echo "Dépôt   : $REPO"
echo "uv      : $UV_BIN"
echo "Version : $VERSION"

# 1. Icônes (PNG + Abyss.icns)
QT_QPA_PLATFORM=offscreen "$UV_BIN" run --project "$REPO" --quiet python "$REPO/scripts/build_icons.py"

# 2. Bundle construit à côté puis échangé (pas d'app à moitié écrite)
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
BUNDLE="$STAGE/Abyss.app"
mkdir -p "$BUNDLE/Contents/MacOS" "$BUNDLE/Contents/Resources"
cp "$REPO/src/abyss/ui/assets/icon/Abyss.icns" "$BUNDLE/Contents/Resources/Abyss.icns"

# Python embarqué : copie de l'interpréteur du venv dans le bundle. macOS rattache ainsi le processus
# d'Abyss à Abyss.app (nom « Abyss » et icône dans le Dock, au lieu de « python3.11 »).
# Bibliothèques et site-packages restent ceux du dépôt (liens symboliques) : rien n'est dupliqué.
read -r PY_BASE PY_LIB SITE < <("$UV_BIN" run --project "$REPO" --quiet python -c \
  'import sys, sysconfig; print(sys.base_prefix, f"python{sys.version_info[0]}.{sys.version_info[1]}", sysconfig.get_paths()["purelib"])')
PY_VERSION="${PY_LIB#python}"
mkdir -p "$BUNDLE/Contents/lib/$PY_LIB"
cp "$PY_BASE/bin/$PY_LIB" "$BUNDLE/Contents/MacOS/abyss-python"
ln -s "$PY_BASE/lib/lib$PY_LIB.dylib" "$BUNDLE/Contents/lib/lib$PY_LIB.dylib"   # @executable_path/../lib
ln -s "$SITE" "$BUNDLE/Contents/lib/$PY_LIB/site-packages"
printf 'home = %s/bin\ninclude-system-site-packages = false\nversion = %s\n' "$PY_BASE" "$PY_VERSION" \
  > "$BUNDLE/Contents/pyvenv.cfg"
"$BUNDLE/Contents/MacOS/abyss-python" -c 'import abyss' || { echo "Python embarqué inutilisable." >&2; exit 1; }

cat > "$BUNDLE/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>Abyss</string>
  <key>CFBundleDisplayName</key><string>Abyss</string>
  <key>CFBundleIdentifier</key><string>com.simonssg1.abyss</string>
  <key>CFBundleExecutable</key><string>abyss</string>
  <key>CFBundleIconFile</key><string>Abyss</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>${VERSION}</string>
  <key>CFBundleVersion</key><string>${VERSION}</string>
  <key>LSMinimumSystemVersion</key><string>12.0</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>LSUIElement</key><true/>
  <key>NSMicrophoneUsageDescription</key><string>Abyss utilise ton micro pour transformer ta voix en temps réel.</string>
</dict>
</plist>
PLIST

# Lanceur natif (Swift) : chemins absolus du dépôt et de uv figés au moment du build,
# car une app lancée depuis le Finder n'hérite pas du PATH du terminal.
if ! command -v swiftc >/dev/null; then
  echo "swiftc introuvable : installe les outils de ligne de commande (xcode-select --install)." >&2
  exit 1
fi
sed -e "s|__REPO__|$REPO|g" -e "s|__UV__|$UV_BIN|g" "$REPO/scripts/macos_launcher.swift" > "$STAGE/launcher.swift"
swiftc -O -o "$BUNDLE/Contents/MacOS/abyss" "$STAGE/launcher.swift"

codesign --force --deep -s - "$BUNDLE"

mkdir -p "$APP_DIR"
rm -rf "$APP"
mv "$BUNDLE" "$APP"
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "$APP" || true
echo "App     : $APP"

# Signature ad hoc = nouvelle identité à chaque build : les autorisations de l'ancien build ne correspondent
# plus et macOS ne redemande pas. On efface celles d'Abyss (et seulement d'Abyss) pour qu'il redemande.
for SERVICE in Microphone ListenEvent Accessibility; do
  tccutil reset "$SERVICE" com.simonssg1.abyss >/dev/null 2>&1 || true
done
echo "Autorisations d'Abyss réinitialisées : macOS redemandera le micro et la surveillance du clavier."

# 3. Alias sur le Bureau (remplace un ancien alias « Abyss », ne touche jamais à un vrai fichier)
DESKTOP_ITEM="$HOME/Desktop/Abyss"
if [[ -e "$DESKTOP_ITEM" ]]; then
  KIND="$(mdls -raw -name kMDItemKind "$DESKTOP_ITEM" 2>/dev/null || echo "")"
  if [[ "$KIND" == "Alias" ]] || [[ "$(osascript -e "tell application \"Finder\" to get class of (POSIX file \"$DESKTOP_ITEM\" as alias)" 2>/dev/null)" == "alias file" ]]; then
    rm -f "$DESKTOP_ITEM"
  else
    echo "« $DESKTOP_ITEM » existe et n'est pas un alias : je n'y touche pas, alias non créé." >&2
    exit 0
  fi
fi
osascript >/dev/null <<OSA
tell application "Finder"
  set newAlias to make alias file to (POSIX file "$APP" as alias) at (path to desktop folder)
  set name of newAlias to "Abyss"
end tell
OSA
echo "Alias   : $DESKTOP_ITEM"
echo "Terminé. Double-clique sur « Abyss » sur le Bureau."
