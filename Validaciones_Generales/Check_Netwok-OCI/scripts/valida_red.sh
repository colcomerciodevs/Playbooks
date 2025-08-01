#!/bin/bash

archivo_ips="$HOME/archivo_ips.txt"
archivo_puertos="$HOME/archivo_puertos.txt"
archivo_salida="$HOME/salida_valida_red.csv"

> "$archivo_salida"

# Función portátil para obtener la IP local principal (IPv4)
get_local_ip() {
  if command -v ip &>/dev/null; then
    ip -o -4 addr show scope global | awk '{print $4}' | cut -d/ -f1 | grep -v '^127' | head -n1
  elif command -v ifconfig &>/dev/null; then
    ifconfig | awk '/inet addr:/{print $2}' | cut -d: -f2 | grep -v '^127' | head -n1
  elif command -v hostname &>/dev/null; then
    hostname -I | awk '{print $1}' | grep -v '^127' | tr -d '\r\n' | xargs
  else
    echo "N/A"
  fi
}

# Obtener datos del sistema y limpiar posibles caracteres ocultos
hostname_actual=$(hostname | tr -d '\r\n' | xargs)
#ip_local=$(hostname -I | awk '{print $1}' | tr -d '\r\n' | xargs)
ip_local=$(get_local_ip)
#gateway=$(ip route | awk '/default/ {print $3}' | tr -d '\r\n' | xargs)
gateway=$(ip route | awk '/^default/ {print $3}' | head -n1 | tr -d '\r\n' | xargs)
interface=$(ip route | awk '/default/ {print $5}' | head -n1 | tr -d '\r\n' | xargs)
cidr=$(ip -o -f inet addr show dev "$interface" | awk '{print $4}' | head -n1 | tr -d '\r\n' | xargs)
prefix=$(echo "$cidr" | cut -d/ -f2 | tr -d '\r\n')

# Convertir CIDR a máscara decimal
mask=$(for i in {1..4}; do
    bits=$(( prefix >= 8 ? 8 : prefix ))
    printf "%d" $(( (255 << (8 - bits)) & 255 ))
    prefix=$(( prefix - bits ))
    [ $i -lt 4 ] && printf "."
done)

# Validar existencia de archivos
[[ ! -s "$archivo_ips" || ! -s "$archivo_puertos" ]] && echo "ERROR: Archivos vacíos" >&2 && exit 1

# Procesar cada IP
grep -v '^\s*$' "$archivo_ips" | while IFS= read -r ip || [[ -n "$ip" ]]; do
  ip=$(echo "$ip" | tr -d '\r\n' | xargs)
  [[ -z "$ip" ]] && continue

  # Validar ping
  if ping -c1 -W1 "$ip" &>/dev/null; then
    estado_ping="Exitoso"
  else
    estado_ping="Fallido"
  fi

  # Imprimir resultado de ping
  printf "%s,%s,%s,%s,%s,ping,N/A,%s\n" "$hostname_actual" "$ip_local" "$mask" "$gateway" "$ip" "$estado_ping" >> "$archivo_salida"

  # Validar puertos
  grep -v '^\s*$' "$archivo_puertos" | while IFS= read -r port || [[ -n "$port" ]]; do
    port=$(echo "$port" | tr -d '\r\n' | xargs)
    [[ -z "$port" ]] && continue

    timeout 1 bash -c "echo > /dev/tcp/$ip/$port" &>/dev/null
    estado_port=$([ $? -eq 0 ] && echo "Abierto" || echo "Cerrado")

    # Imprimir resultado de puerto
    printf "%s,%s,%s,%s,%s,puerto,%s,%s\n" "$hostname_actual" "$ip_local" "$mask" "$gateway" "$ip" "$port" "$estado_port" >> "$archivo_salida"
  done
done

