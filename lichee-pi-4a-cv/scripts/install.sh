#!/usr/bin/env bash
# SCANX — установка на Linux / Lichee Pi 4A
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo ""
echo "  SCANX — установщик (Linux)"
echo "  =========================="
echo ""

find_python() {
  for cmd in python3 python; do
    if command -v "$cmd" >/dev/null 2>&1; then
      ver=$("$cmd" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
      major=${ver%%.*}
      minor=${ver#*.}
      if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
        echo "$cmd"
        return 0
      fi
    fi
  done
  return 1
}

echo "==> Поиск Python 3.10+"
PY=$(find_python) || {
  echo "Python 3.10+ не найден. Ubuntu/Debian: sudo apt install python3 python3-venv python3-pip"
  exit 1
}
echo "  OK: $PY"

echo "==> Виртуальное окружение"
if [ ! -f "$ROOT/.venv/bin/python" ]; then
  "$PY" -m venv "$ROOT/.venv"
fi
VPY="$ROOT/.venv/bin/python"

echo "==> Зависимости"
"$VPY" -m pip install -U pip wheel
"$VPY" -m pip install -r "$ROOT/requirements.txt"

echo "==> Папка videos/"
mkdir -p "$ROOT/videos"

echo "==> Модель YOLOv8n ONNX"
"$VPY" "$ROOT/scripts/download_model.py"

cat > "$ROOT/run.sh" << 'EOF'
#!/usr/bin/env bash
cd "$(dirname "$0")"
exec .venv/bin/python main.py "$@"
EOF
chmod +x "$ROOT/run.sh"

echo ""
echo "  Готово!"
echo "  Запуск: ./run.sh"
echo "          ./run.sh --config config/edge.yaml   # Lichee Pi 4A"
echo "  Браузер: http://127.0.0.1:8080"
echo ""
