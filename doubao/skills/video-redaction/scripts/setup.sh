#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_PATH="${SCRIPT_DIR}/$(basename "${BASH_SOURCE[0]}")"
TELEMETRY_RUNNER="${SCRIPT_DIR}/telemetry_runner.py"
TELEMETRY_MODULE="${SCRIPT_DIR}/telemetry.py"
TELEMETRY_PYTHON="$(command -v python3 2>/dev/null || command -v python 2>/dev/null || true)"

if [ "${VIDEO_REDACTION_TELEMETRY_ACTIVE:-0}" != "1" ] \
    && [ -f "$TELEMETRY_RUNNER" ] \
    && [ -f "$TELEMETRY_MODULE" ] \
    && [ -n "$TELEMETRY_PYTHON" ]; then
    export VIDEO_REDACTION_TELEMETRY_ACTIVE=1
    exec "$TELEMETRY_PYTHON" "$TELEMETRY_RUNNER" \
        --entry-file "$SCRIPT_PATH" \
        --command "setup" \
        --runtime "bash" \
        -- /bin/bash "$SCRIPT_PATH" "$@"
fi

set -euo pipefail

for standard_bin in /opt/homebrew/bin /usr/local/bin /usr/bin /bin /usr/sbin /sbin; do
    case ":${PATH:-}:" in
        *":${standard_bin}:"*) ;;
        *) PATH="${PATH:+${PATH}:}${standard_bin}" ;;
    esac
done
export PATH

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

FUNASR_CHECK_CODE=$'import importlib.util\nimport torch, modelscope, kaldi_native_fbank\nspec = importlib.util.find_spec("funasr")\nassert spec is not None, "funasr package not found"\nprint("funasr-ready")'

venv_python() {
    local venv="$1"
    if [ -x "${venv}/bin/python3" ]; then
        echo "${venv}/bin/python3"
    elif [ -x "${venv}/Scripts/python.exe" ]; then
        echo "${venv}/Scripts/python.exe"
    else
        return 1
    fi
}

SUPPORTED_PY_HINT="Python 3.10-3.13 (macOS: 'brew install python@3.12'; Debian/Ubuntu: 'sudo apt-get install python3.12 python3.12-venv')"

# FunASR deps (torch / kaldi-native-fbank) only ship prebuilt wheels for 3.10-3.13.
# 3.14 has no wheels and we refuse source builds, so treat it as unsupported.
python_version_supported() {
    local python="$1" ver
    [ -n "$python" ] || return 1
    ver="$("$python" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null)" || return 1
    case "$ver" in
        3.10|3.11|3.12|3.13) return 0 ;;
        *) return 1 ;;
    esac
}

pick_base_python() {
    local cand path
    for cand in python3.12 python3.11 python3.10 python3.13 python3 python; do
        path="$(command -v "$cand" 2>/dev/null)" || continue
        if python_version_supported "$path"; then
            printf '%s\n' "$path"
            return 0
        fi
    done
    return 1
}

# Can we auto-install a supported Python on this host without user help?
python_autoinstaller_available() {
    case "$(uname -s 2>/dev/null || true)" in
        Darwin*) command -v brew >/dev/null 2>&1 ;;
        Linux*)
            [ "$(id -u)" -eq 0 ] \
                && { command -v apt-get >/dev/null 2>&1 || command -v dnf >/dev/null 2>&1; }
            ;;
        *) return 1 ;;
    esac
}

echo -e "${GREEN}Starting local media environment setup...${NC}"

case "$(uname -s 2>/dev/null || echo Windows)" in
    Darwin*|Linux*) VENV_HOME="${HOME}/.local/share/funasr_env" ;;
    *)              VENV_HOME="${LOCALAPPDATA:-$HOME/AppData/Local}/funasr_env" ;;
esac

READY_FILE="${VENV_HOME}/.ready"
LOCK_FILE="${VENV_HOME}/.installing"
PYTHON_FILE="${VENV_HOME}/.python"
FFMPEG_FILE="${VENV_HOME}/.ffmpeg"
LOG_FILE="${VENV_HOME}/setup.log"
TORCH_CPU_INDEX="https://download.pytorch.org/whl/cpu"

mkdir -p "$VENV_HOME"

if [ "${FUNASR_SETUP_WORKER:-0}" != "1" ]; then
    FUNASR_SETUP_WORKER=1 nohup /bin/bash "$0" > "$LOG_FILE" 2>&1 < /dev/null &
    echo -e "${GREEN}Local media setup started in background (PID=$!, log=${LOG_FILE}).${NC}"
    exit 0
fi

read_first_line() {
    local value=""
    [ -r "$1" ] || return 1
    IFS= read -r value < "$1" || [ -n "$value" ] || return 1
    printf '%s\n' "$value"
}

python_is_ready() {
    local python="$1"
    [ -n "$python" ] && "$python" -c "$FUNASR_CHECK_CODE" >/dev/null 2>&1
}

mark_ready() {
    local python="$1"
    printf '%s\n' "$python" > "${PYTHON_FILE}.tmp.$$"
    mv "${PYTHON_FILE}.tmp.$$" "$PYTHON_FILE"
    touch "$READY_FILE"
}

install_funasr_dependencies() {
    local python="$1"
    "$python" -m pip install --index-url "$TORCH_CPU_INDEX" torch \
        && "$python" -m pip install --only-binary=:all: kaldi-native-fbank \
        && "$python" -m pip install funasr modelscope
}

ensure_ffmpeg() {
    local ffmpeg_path
    local os_name

    if command -v ffmpeg >/dev/null 2>&1 \
        && command -v ffprobe >/dev/null 2>&1; then
        ffmpeg_path="$(command -v ffmpeg)"
        printf '%s\n' "$ffmpeg_path" > "${FFMPEG_FILE}.tmp.$$"
        mv "${FFMPEG_FILE}.tmp.$$" "$FFMPEG_FILE"
        echo -e "${GREEN}ffmpeg already ready: ${ffmpeg_path}${NC}"
        return 0
    fi

    rm -f "$FFMPEG_FILE"
    os_name="$(uname -s 2>/dev/null || true)"
    case "$os_name" in
        Darwin*)
            if ! command -v brew >/dev/null 2>&1; then
                echo -e "${RED}ffmpeg is missing and Homebrew is unavailable. Install Homebrew, then rerun setup.${NC}"
                return 1
            fi
            echo "ffmpeg is missing; installing with Homebrew..."
            HOMEBREW_NO_AUTO_UPDATE=1 brew install ffmpeg
            ;;
        Linux*)
            if [ "$(id -u)" -eq 0 ] && command -v apt-get >/dev/null 2>&1; then
                apt-get update
                apt-get install -y ffmpeg
            elif [ "$(id -u)" -eq 0 ] && command -v dnf >/dev/null 2>&1; then
                dnf install -y ffmpeg
            else
                echo -e "${RED}ffmpeg is missing. Install it with the host Linux package manager, then rerun setup.${NC}"
                return 1
            fi
            ;;
        *)
            echo -e "${RED}Unsupported platform for setup.sh ffmpeg installation: ${os_name}${NC}"
            return 1
            ;;
    esac

    command -v ffmpeg >/dev/null 2>&1 \
        && command -v ffprobe >/dev/null 2>&1 || {
        echo -e "${RED}ffmpeg installation finished but ffmpeg/ffprobe is still unavailable.${NC}"
        return 1
    }

    ffmpeg_path="$(command -v ffmpeg)"
    printf '%s\n' "$ffmpeg_path" > "${FFMPEG_FILE}.tmp.$$"
    mv "${FFMPEG_FILE}.tmp.$$" "$FFMPEG_FILE"
    echo -e "${GREEN}ffmpeg setup complete: ${ffmpeg_path}${NC}"
}

# Ensure a FunASR-compatible base Python (3.10-3.13) exists, echoing its path.
# Auto-installs one when the host has a usable package manager; otherwise prints
# a clear prompt and fails so the caller can stop instead of building from source.
ensure_base_python() {
    local base os_name

    if base="$(pick_base_python)"; then
        printf '%s\n' "$base"
        return 0
    fi

    os_name="$(uname -s 2>/dev/null || true)"
    if ! python_autoinstaller_available; then
        echo -e "${RED}No compatible Python found. Install ${SUPPORTED_PY_HINT}, then rerun setup.${NC}" >&2
        return 1
    fi

    case "$os_name" in
        Darwin*)
            echo "No compatible Python found; installing python@3.12 with Homebrew..." >&2
            HOMEBREW_NO_AUTO_UPDATE=1 brew install python@3.12 >&2
            ;;
        Linux*)
            if command -v apt-get >/dev/null 2>&1; then
                apt-get update >&2
                apt-get install -y python3.12 python3.12-venv >&2
            else
                dnf install -y python3.12 >&2
            fi
            ;;
    esac

    if base="$(pick_base_python)"; then
        printf '%s\n' "$base"
        return 0
    fi

    echo -e "${RED}Python auto-install finished but no compatible interpreter (3.10-3.13) is available. Install ${SUPPORTED_PY_HINT} manually, then rerun setup.${NC}" >&2
    return 1
}

acquire_install_lock() {
    local lock_pid

    if (set -o noclobber; printf '%s\n' "$$" > "$LOCK_FILE") 2>/dev/null; then
        return 0
    fi

    lock_pid="$(read_first_line "$LOCK_FILE" 2>/dev/null || true)"
    if [[ "$lock_pid" =~ ^[0-9]+$ ]] && kill -0 "$lock_pid" 2>/dev/null; then
        return 1
    fi

    rm -f "$LOCK_FILE"
    (set -o noclobber; printf '%s\n' "$$" > "$LOCK_FILE") 2>/dev/null
}

if ! acquire_install_lock; then
    echo -e "${YELLOW}Local media setup is already running; reusing that installation.${NC}"
    exit 0
fi

trap 'rm -f "$LOCK_FILE"' EXIT

ensure_ffmpeg || {
    rm -f "$READY_FILE"
    exit 1
}

if [ -f "$READY_FILE" ]; then
    FUNASR_PY="$(read_first_line "$PYTHON_FILE" 2>/dev/null || true)"
    if python_is_ready "$FUNASR_PY"; then
        echo -e "${GREEN}FunASR already ready: ${FUNASR_PY}${NC}"
        exit 0
    fi

    if FUNASR_PY="$(venv_python "$VENV_HOME")" \
        && python_is_ready "$FUNASR_PY"; then
        mark_ready "$FUNASR_PY"
        echo -e "${GREEN}FunASR already ready: ${FUNASR_PY}${NC}"
        exit 0
    fi

    if SYSTEM_PY="$(command -v python3 2>/dev/null)" \
        && python_is_ready "$SYSTEM_PY"; then
        mark_ready "$SYSTEM_PY"
        echo -e "${GREEN}FunASR already ready: ${SYSTEM_PY}${NC}"
        exit 0
    fi

    rm -f "$READY_FILE" "$PYTHON_FILE"
fi

if SYSTEM_PY="$(command -v python3 2>/dev/null)" \
    && python_is_ready "$SYSTEM_PY"; then
    echo -e "${GREEN}System python3 already satisfies FunASR dependencies.${NC}"
    mark_ready "$SYSTEM_PY"
    echo "FUNASR_PY=${SYSTEM_PY}"
    exit 0
fi

if FUNASR_PY="$(venv_python "$VENV_HOME")" \
    && python_is_ready "$FUNASR_PY"; then
    echo -e "${GREEN}Reusing existing FunASR venv: ${FUNASR_PY}${NC}"
    mark_ready "$FUNASR_PY"
    echo "FUNASR_PY=${FUNASR_PY}"
    exit 0
fi

if [ -n "${SYSTEM_PY:-}" ] \
    && python_version_supported "$SYSTEM_PY" \
    && "$SYSTEM_PY" -m pip --version >/dev/null 2>&1 \
    && install_funasr_dependencies "$SYSTEM_PY" \
    && python_is_ready "$SYSTEM_PY"; then
    echo -e "${GREEN}Installed FunASR dependencies into system python3.${NC}"
    mark_ready "$SYSTEM_PY"
    echo "FUNASR_PY=${SYSTEM_PY}"
    exit 0
fi

BASE_PY="$(ensure_base_python)" || exit 1

if [ ! -x "${VENV_HOME}/bin/python3" ] && [ ! -x "${VENV_HOME}/Scripts/python.exe" ]; then
    echo "Creating venv at ${VENV_HOME} with ${BASE_PY}..."
    "$BASE_PY" -m venv "$VENV_HOME"
fi

FUNASR_PY="$(venv_python "$VENV_HOME")" || {
    echo -e "${RED}Failed to locate python in venv: ${VENV_HOME}${NC}"
    exit 1
}

echo "Installing FunASR dependencies into ${VENV_HOME}..."
"$FUNASR_PY" -m pip install --upgrade pip
install_funasr_dependencies "$FUNASR_PY"

python_is_ready "$FUNASR_PY" || {
    echo -e "${RED}FunASR import verification failed inside venv.${NC}"
    exit 1
}

mark_ready "$FUNASR_PY"
echo -e "${GREEN}FunASR setup complete.${NC}"
echo "FUNASR_PY=${FUNASR_PY}"
