#!/usr/bin/env bash
set -euo pipefail

REPO="https://github.com/brkylmzco/skyproject.git"
INSTALL_DIR="${SKYPROJECT_DIR:-$HOME/SkyProject}"
MIN_PYTHON="3.10"

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}"
cat << 'BANNER'
  _____ _          ____            _           _
 / ____| |        |  _ \          (_)         | |
| (___ | | ___   _| |_) |_ __ ___  _  ___  __| |_
 \___ \| |/ / | | |  __/| '__/ _ \| |/ _ \/ _  __\
 ____) |   <| |_| | |   | | | (_) | |  __/ (_| |_
|_____/|_|\_\\__, |_|   |_|  \___/| |\___|\___\__|
              __/ |              _/ |
             |___/              |__/
BANNER
echo -e "${NC}"
echo -e "${GREEN}Self-evolving AI development system${NC}"
echo ""

check_python() {
    for cmd in python3 python; do
        if command -v "$cmd" &>/dev/null; then
            version=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
            major=$("$cmd" -c "import sys; print(sys.version_info.major)")
            minor=$("$cmd" -c "import sys; print(sys.version_info.minor)")
            if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
                PYTHON_CMD="$cmd"
                echo -e "${GREEN}Found Python $version ($cmd)${NC}"
                return 0
            fi
        fi
    done
    echo -e "${RED}Python $MIN_PYTHON+ is required but not found.${NC}"
    echo "  Install Python 3.10+: https://www.python.org/downloads/"
    exit 1
}

check_git() {
    if ! command -v git &>/dev/null; then
        echo -e "${RED}Git is required but not found.${NC}"
        exit 1
    fi
    echo -e "${GREEN}Git found${NC}"
}

clone_repo() {
    if [ -d "$INSTALL_DIR/.git" ]; then
        echo -e "${YELLOW}Existing installation found, pulling latest...${NC}"
        cd "$INSTALL_DIR"
        git pull --ff-only || true
    else
        echo -e "${CYAN}Cloning SkyProject...${NC}"
        git clone "$REPO" "$INSTALL_DIR"
        cd "$INSTALL_DIR"
    fi
    echo -e "${GREEN}Repository ready${NC}"
}

setup_venv() {
    if [ ! -d "$INSTALL_DIR/venv" ]; then
        echo -e "${CYAN}Creating virtual environment...${NC}"
        "$PYTHON_CMD" -m venv "$INSTALL_DIR/venv"
    fi
    # shellcheck disable=SC1091
    source "$INSTALL_DIR/venv/bin/activate"
    echo -e "${GREEN}Virtual environment activated${NC}"
}

install_deps() {
    echo -e "${CYAN}Installing dependencies...${NC}"
    pip install --quiet --upgrade pip
    pip install --quiet -e "$INSTALL_DIR"
    echo -e "${GREEN}Dependencies installed${NC}"
}

configure_env() {
    ENV_FILE="$INSTALL_DIR/.env"
    if [ -f "$ENV_FILE" ]; then
        echo -e "${YELLOW}.env already exists, skipping configuration.${NC}"
        return
    fi

    cp "$INSTALL_DIR/.env.example" "$ENV_FILE"

    echo ""
    echo -e "${CYAN}-- API Key Configuration --${NC}"
    echo ""

    echo "Choose LLM provider:"
    echo "  1) OpenAI (default)"
    echo "  2) Anthropic (Claude)"
    read -rp "Enter choice [1]: " provider_choice
    provider_choice="${provider_choice:-1}"

    if [ "$provider_choice" = "2" ]; then
        sed -i 's/^LLM_PROVIDER=.*/LLM_PROVIDER=anthropic/' "$ENV_FILE"
        sed -i 's/^LLM_MODEL=.*/LLM_MODEL=claude-sonnet-4-20250514/' "$ENV_FILE"
        read -rp "Enter your Anthropic API key: " api_key
        if [ -n "$api_key" ]; then
            if grep -q "^ANTHROPIC_API_KEY=" "$ENV_FILE"; then
                sed -i "s|^ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=$api_key|" "$ENV_FILE"
            else
                echo "ANTHROPIC_API_KEY=$api_key" >> "$ENV_FILE"
            fi
        fi
    else
        read -rp "Enter your OpenAI API key: " api_key
        if [ -n "$api_key" ]; then
            sed -i "s|^OPENAI_API_KEY=.*|OPENAI_API_KEY=$api_key|" "$ENV_FILE"
        fi
    fi

    echo ""
    read -rp "Configure Telegram bot? (y/N): " tg_choice
    if [ "${tg_choice,,}" = "y" ]; then
        read -rp "  Telegram Bot Token: " tg_token
        read -rp "  Telegram Chat ID: " tg_chat
        if [ -n "$tg_token" ]; then
            echo "TELEGRAM_BOT_TOKEN=$tg_token" >> "$ENV_FILE"
        fi
        if [ -n "$tg_chat" ]; then
            echo "TELEGRAM_CHAT_ID=$tg_chat" >> "$ENV_FILE"
        fi
    fi

    echo -e "${GREEN}Configuration saved to .env${NC}"
}

run_init() {
    echo -e "${CYAN}Initializing SkyProject...${NC}"
    # shellcheck disable=SC1091
    source "$INSTALL_DIR/venv/bin/activate"
    skyproject init
    echo -e "${GREEN}Initialization complete${NC}"
}

echo "Installing SkyProject to: $INSTALL_DIR"
echo ""

check_python
check_git
clone_repo
setup_venv
install_deps
configure_env
run_init

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  SkyProject installed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "  ${CYAN}Quick start:${NC}"
echo ""
echo "    cd $INSTALL_DIR"
echo "    source venv/bin/activate"
echo ""
echo -e "    ${CYAN}skyproject run${NC}      # Start AI development loop"
echo -e "    ${CYAN}skyproject web${NC}      # Start Web UI on :8080"
echo -e "    ${CYAN}skyproject status${NC}   # Check system status"
echo ""
