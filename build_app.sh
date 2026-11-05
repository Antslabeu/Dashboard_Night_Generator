#!/bin/zsh

set -euo pipefail

SCRIPT_DIRECTORY="${0:A:h}"
cd "$SCRIPT_DIRECTORY"

if [[ ! -x ".venv/bin/python" ]]; then
    print -u2 "Brak środowiska .venv. Utwórz je zgodnie z README."
    exit 1
fi

.venv/bin/python -m PyInstaller \
    --noconfirm \
    --clean \
    --windowed \
    --name "Dashboard Generator" \
    --icon "assets/app-icon.icns" \
    --osx-bundle-identifier "pl.konrad.dashboard-generator" \
    app.py

print
print "Gotowe:"
print "$SCRIPT_DIRECTORY/dist/Dashboard Generator.app"
