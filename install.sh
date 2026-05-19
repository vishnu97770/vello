#!/bin/bash
set -e

echo ""
echo "╔══════════════════════════════════════╗"
echo "║  VELLO — Linux Voice Assistant      ║"
echo "║  Installer v1.0                     ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ── 1. Detect distro ─────────────────────────────────────────────────────────
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO="$ID"
else
    echo "ERROR: Cannot detect Linux distribution."
    exit 1
fi

echo "Detected distro: $DISTRO"
echo ""

# ── 2. Install system packages ───────────────────────────────────────────────
case "$DISTRO" in
    ubuntu|debian|linuxmint|pop)
        echo "Installing system packages (apt)..."
        sudo apt-get update -q
        sudo apt-get install -y \
            python3 python3-pip python3-venv \
            portaudio19-dev libportaudio2 \
            espeak espeak-ng mpv \
            xclip wl-clipboard \
            libnotify-bin \
            network-manager \
            scrot gnome-screenshot \
            wmctrl xdotool \
            alsa-utils \
            wget unzip
        ;;
    fedora|rhel|centos)
        echo "Installing system packages (dnf)..."
        sudo dnf install -y \
            python3 python3-pip portaudio-devel \
            espeak espeak-ng mpv \
            xclip wl-clipboard libnotify \
            NetworkManager scrot wmctrl xdotool \
            alsa-utils \
            wget unzip
        ;;
    arch|manjaro|endeavouros)
        echo "Installing system packages (pacman)..."
        sudo pacman -Sy --noconfirm \
            python python-pip portaudio \
            espeak-ng mpv \
            xclip wl-clipboard libnotify \
            networkmanager scrot wmctrl xdotool \
            alsa-utils \
            wget unzip
        ;;
    opensuse*|suse)
        echo "Installing system packages (zypper)..."
        sudo zypper install -y \
            python3 python3-pip portaudio-devel \
            espeak mpv xclip libnotify4 \
            NetworkManager scrot wmctrl xdotool \
            alsa-utils \
            wget unzip
        ;;
    *)
        echo "ERROR: Unsupported distribution: $DISTRO"
        echo ""
        echo "Please install these packages manually:"
        echo "  python3 python3-pip python3-venv portaudio-devel"
        echo "  espeak mpv xclip nmcli scrot wmctrl xdotool alsa-utils"
        exit 1
        ;;
esac

echo ""
echo "✓ System packages installed"

# ── 3. Create Python venv ────────────────────────────────────────────────────
VELLO_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$VELLO_ROOT"

echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "✓ Python environment ready"

# ── 4. Download Vosk model ───────────────────────────────────────────────────
MODEL_DIR="$HOME/.vello/models"
MODEL_NAME="vosk-model-small-en-us-0.15"
MODEL_PATH="$MODEL_DIR/vosk-model-small-en-us"
MODEL_URL="https://alphacephei.com/vosk/models/${MODEL_NAME}.zip"

if [ -d "$MODEL_PATH" ]; then
    echo "✓ Vosk model already present, skipping."
else
    echo "Downloading Vosk speech recognition model (~50 MB)..."
    mkdir -p "$MODEL_DIR"
    if command -v wget &>/dev/null; then
        wget -q --show-progress -P "$MODEL_DIR" "$MODEL_URL"
    elif command -v curl &>/dev/null; then
        curl -L -o "$MODEL_DIR/${MODEL_NAME}.zip" "$MODEL_URL"
    else
        echo "ERROR: wget or curl required to download model."
        exit 1
    fi
    unzip -q "$MODEL_DIR/${MODEL_NAME}.zip" -d "$MODEL_DIR"
    mv "$MODEL_DIR/$MODEL_NAME" "$MODEL_PATH"
    rm -f "$MODEL_DIR/${MODEL_NAME}.zip"
    echo "✓ Vosk model downloaded"
fi

# ── 5. Copy .env template ────────────────────────────────────────────────────
if [ ! -f "$VELLO_ROOT/.env" ]; then
    if [ -f "$VELLO_ROOT/.env.example" ]; then
        cp "$VELLO_ROOT/.env.example" "$VELLO_ROOT/.env"
        echo "✓ Created .env from template — add your OpenAI API key"
    else
        echo "OPENAI_API_KEY=your_key_here" > "$VELLO_ROOT/.env"
        echo "✓ Created .env — add your OpenAI API key"
    fi
else
    echo "✓ .env already exists, skipping."
fi

# ── 6. Install systemd service ───────────────────────────────────────────────
echo "Installing systemd user service..."
source "$VELLO_ROOT/venv/bin/activate"
python "$VELLO_ROOT/scripts/install_service.py"
echo "✓ systemd service installed"

# ── 7. Print summary ─────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  Installation complete!                     ║"
echo "╠══════════════════════════════════════════════╣"
echo "║  ✓ System packages installed                ║"
echo "║  ✓ Python environment ready                 ║"
echo "║  ✓ Vosk model downloaded                    ║"
echo "║  ✓ systemd service installed                ║"
echo "╠══════════════════════════════════════════════╣"
echo "║  Start Vello now:                           ║"
echo "║    systemctl --user start vello             ║"
echo "║                                             ║"
echo "║  Or run directly:                           ║"
echo "║    source venv/bin/activate                 ║"
echo "║    python main.py                           ║"
echo "╠══════════════════════════════════════════════╣"
echo "║  Optional — better voice quality:           ║"
echo "║    source venv/bin/activate                 ║"
echo "║    python -m vello.tts.piper_setup          ║"
echo "╠══════════════════════════════════════════════╣"
echo "║  Optional — custom wake word:               ║"
echo "║    python scripts/train_wake_word.py        ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
