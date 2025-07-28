#!/bin/bash

# 📂 Archivos de entrada y salida ubicados en el HOME del usuario remoto
archivo_ips="$HOME/archivo_ips.txt"
archivo_puertos="$HOME/archivo_puertos.txt"
archivo_salida="$HOME/salida_valida_red.csv"

# 🧹 Limpiar archivo de salida (si existe)
> "$archivo_salida"

# 🖥️ Obtener información del sistema
hostname_actual=$(hostname)
ip_local=$(hostname -I | awk '{print $1}')
gateway=$(ip route | awk '/default/ {print $3}')
interface=$(ip route | awk '/default/ {print $5}' | head -n1)
cidr=$(ip -o -f inet addr show dev "$interface" | awk '{print $4}' | head -n1)
prefix=$(echo "$cidr" | cut -d/ -f2)

# 🎯 Convertir el prefijo CIDR a máscara decimal
mask=$(for i in {1..4}; do
    bits=$(( prefix >= 8 ? 8 : prefix ))
    echo -n "$(( (255 << (8 - bits)) & 255 ))"
    prefix=$(( prefix - bits ))
    [ $i -lt 4 ] && echo -n "."
done)

# 🚫 Validar que los archivos existan y tengan contenido
[[ ! -s "$archivo_ips" || ! -s "$archivo_puertos" ]] && echo "ERROR: Archivos vacíos" >&2 && exit 1

# 🔁 Validar conectividad IP por IP
grep -v '^\s*$' "$archivo_ips" | while IFS= read -r ip || [[ -n "$ip" ]]; do
  ip=$(echo "$ip" | tr -d '\r' | xargs)  # Limpieza de espacios y \r
  [[ -z "$ip" ]] && continue

  # 🟢 Validar conectividad (ping)
  ping -c1 -W1 "$ip" &> /dev/null
  estado_ping=$([ $? -eq 0 ] && echo "Exitoso" || echo "Fallido")
  echo "$hostname_actual,$ip_local,$mask,$gateway,ping,$ip,N/A,$estado_ping" >> "$archivo_salida"

  # 🔁 Validar puertos para esa IP
  grep -v '^\s*$' "$archivo_puertos" | while IFS= read -r port || [[ -n "$port" ]]; do
    port=$(echo "$port" | tr -d '\r' | xargs)
    [[ -z "$port" ]] && continue

    # ⚡ Validación rápida con /dev/tcp
    timeout 1 bash -c "echo > /dev/tcp/$ip/$port" &> /dev/null
    estado_port=$([ $? -eq 0 ] && echo "Abierto" || echo "Cerrado")

    echo "$hostname_actual,$ip_local,$mask,$gateway,puerto,$ip,$port,$estado_port" >> "$archivo_salida"
  done
done
