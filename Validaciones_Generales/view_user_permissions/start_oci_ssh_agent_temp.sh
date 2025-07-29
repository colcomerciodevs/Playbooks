#!/bin/bash

KEY_PATH="/root/.ssh/adminso-psdev.pem"

# Validar que la clave exista
if [ ! -f "$KEY_PATH" ]; then
  echo "❌ Clave no encontrada en $KEY_PATH"
  exit 1
fi

# Si ya hay un agente activo y accesible
if [ -n "$SSH_AUTH_SOCK" ] && ssh-add -l >/dev/null 2>&1; then
  echo "🟢 ssh-agent ya está activo y funcional."
else
  echo "🔐 Iniciando nuevo ssh-agent..."
  eval "$(ssh-agent -s)"

  echo "➕ Agregando clave $KEY_PATH..."
  ssh-add "$KEY_PATH"
fi

# Mostrar estado final
ssh-add -l
echo ""
echo "✅ ssh-agent listo. Puedes ejecutar Ansible sin que se solicite passphrase."
