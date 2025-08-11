#!/bin/bash
#
# valida_red.sh
#
# Genera un CSV con:
# host, ip_local, mascara, gateway, destino, (ping|puerto), valor, estado
#
# Correcciones clave:
# - Limpieza robusta de espacios Unicode y caracteres no-ASCII invisibles
#   que causaban secuencias raras en el CSV (p. ej. â€‚).
# - Normalización de entradas (IPs, puertos) y datos del sistema.
#

# ================== Parámetros ==================
archivo_ips="$HOME/archivo_ips.txt"
archivo_puertos="$HOME/archivo_puertos.txt"
archivo_salida="$HOME/salida_valida_red.csv"

# Timeouts (segundos)
PING_TIMEOUT=1
PORT_TIMEOUT=2
TELNET_TIMEOUT=5

# Asegurar entorno C para que [:print:] considere solo ASCII
# (esto ayuda a que NBSP/ZWSP y demás NO sean "printables")
export LC_ALL=C

# Limpiar archivo de salida
: > "$archivo_salida"

# ================== Utilidades portátiles ==================

# Ejecuta un comando con timeout aunque no exista `timeout` (GNU coreutils)
run_with_timeout() {
  local dur="$1"; shift
  if command -v timeout >/dev/null 2>&1; then
    timeout "$dur" "$@"
    return $?
  else
    "$@" &
    local cmd_pid=$!
    (
      sleep "$dur"
      kill -0 "$cmd_pid" 2>/dev/null && kill -9 "$cmd_pid" 2>/dev/null
    ) &
    local watcher=$!
    wait "$cmd_pid" 2>/dev/null
    local rc=$?
    kill -0 "$watcher" 2>/dev/null && kill "$watcher" 2>/dev/null
    return $rc
  fi
}

# --------- Sanitización de texto (CLAVE PARA EL CSV) ---------
# Quita CR/LF, recorta, elimina caracteres no ASCII/invisibles (NBSP, ZWSP, BOM, etc.)
sanitize_field() {
  # 1) quitar CR/LF
  # 2) eliminar caracteres no imprimibles ASCII (incluye bytes de NBSP/ZWSP en LC_ALL=C)
  # 3) colapsar espacios múltiples a 1 espacio
  # 4) recortar espacios al inicio/fin
  printf '%s' "$*" \
    | tr -d '\r\n' \
    | sed -e 's/[^[:print:]\t]//g' -e 's/[[:space:]]\+/ /g' \
    | xargs
}

# IP local principal (IPv4)
get_local_ip() {
  if command -v ip >/dev/null 2>&1; then
    ip -o -4 addr show scope global 2>/dev/null | awk '{print $4}' | cut -d/ -f1 | grep -v '^127' | head -n1
  elif command -v ifconfig >/dev/null 2>&1; then
    ifconfig 2>/dev/null | awk '/inet (addr:)?[0-9]/ && $2 !~ /^127/ {for(i=1;i<=NF;i++) if ($i ~ /inet|addr:/) print $i}' \
      | sed -E 's/inet addr:|inet //g' | awk 'NR==1{print; exit}'
  elif command -v hostname >/dev/null 2>&1; then
    hostname -I 2>/dev/null | awk '{print $1}' | grep -v '^127' | tr -d '\r\n' | xargs
  else
    echo "N/A"
  fi
}

# Interfaz por defecto y gateway
get_default_route() {
  if command -v ip >/dev/null 2>&1; then
    local gw iface
    gw=$(ip route 2>/dev/null | awk '/^default/{print $3; exit}')
    iface=$(ip route 2>/dev/null | awk '/^default/{print $5; exit}')
    echo "$gw|$iface"
  elif command -v route >/dev/null 2>&1; then
    local line gw iface
    line=$(route -n 2>/dev/null | awk '$1=="0.0.0.0"{print; exit}')
    gw=$(awk '{print $2}' <<<"$line")
    iface=$(awk '{print $8}' <<<"$line")
    echo "$gw|$iface"
  elif command -v netstat >/dev/null 2>&1; then
    local line gw iface
    line=$(netstat -rn 2>/dev/null | awk '$1=="default" || $1=="0.0.0.0"{print; exit}')
    gw=$(awk '{print $2}' <<<"$line")
    iface=$(awk '{print $NF}' <<<"$line")
    echo "$gw|$iface"
  else
    echo "N/A|N/A"
  fi
}

# CIDR de la interfaz (si hay `ip`), si no, intenta con ifconfig
get_iface_cidr() {
  local iface="$1"
  if [[ -z "$iface" || "$iface" == "N/A" ]]; then
    echo ""
    return
  fi
  if command -v ip >/dev/null 2>&1; then
    ip -o -f inet addr show dev "$iface" 2>/dev/null | awk '{print $4}' | head -n1
  elif command -v ifconfig >/dev/null 2>&1; then
    local ip mask prefix
    ip=$(ifconfig "$iface" 2>/dev/null | awk '/inet (addr:)?[0-9]/ {for(i=1;i<=NF;i++) if ($i ~ /inet|addr:/) print $i}' \
          | sed -E 's/inet addr:|inet //g' | head -n1)
    mask=$(ifconfig "$iface" 2>/dev/null | awk '/Mask:|netmask/{for(i=1;i<=NF;i++) if ($i ~ /Mask:|netmask/) print $i}' \
           | sed -E 's/Mask:|netmask //g' | head -n1)
    if [[ "$mask" =~ ^0x ]]; then
      mask=$(printf "%d.%d.%d.%d" $(( (0x${mask:2}>>24)&255 )) $(( (0x${mask:2}>>16)&255 )) $(( (0x${mask:2}>>8)&255 )) $(( 0x${mask:2}&255 )))
    fi
    if [[ "$ip" =~ ^[0-9.]+$ && "$mask" =~ ^[0-9.]+$ ]]; then
      IFS='.' read -r a b c d <<<"$mask"
      local bits=0 x
      for x in $a $b $c $d; do
        case "$x" in
          255) bits=$((bits+8));;
          254) bits=$((bits+7));;
          252) bits=$((bits+6));;
          248) bits=$((bits+5));;
          240) bits=$((bits+4));;
          224) bits=$((bits+3));;
          192) bits=$((bits+2));;
          128) bits=$((bits+1));;
          0) ;;
          *) bits=""; break;;
        esac
      done
      [[ -n "$bits" ]] && echo "$ip/$bits" || echo ""
    else
      echo ""
    fi
  else
    echo ""
  fi
}

# Máscara desde prefijo
prefix_to_mask() {
  local prefix="$1"
  [[ -z "$prefix" ]] && { echo "N/A"; return; }
  local i bits out=""
  for i in 1 2 3 4; do
    bits=$(( prefix >= 8 ? 8 : (prefix>0?prefix:0) ))
    out+=$(( (255 << (8 - bits)) & 255 ))
    prefix=$(( prefix - bits ))
    [[ $i -lt 4 ]] && out+="."
  done
  echo "$out"
}

# ================== Datos del sistema ==================
hostname_actual=$(sanitize_field "$(hostname 2>/dev/null)")
ip_local=$(sanitize_field "$(get_local_ip)")

IFS='|' read -r gateway interface <<<"$(get_default_route)"
gateway=$(sanitize_field "$gateway")
interface=$(sanitize_field "$interface")

cidr=$(get_iface_cidr "$interface")
cidr=$(sanitize_field "$cidr")

prefix=$(echo "$cidr" | awk -F/ 'NF==2{print $2}')
mask=$(prefix_to_mask "$prefix")
mask=$(sanitize_field "$mask")

# ================== Validaciones previas ==================
if [[ ! -s "$archivo_ips" || ! -s "$archivo_puertos" ]]; then
  echo "ERROR: Archivos vacíos o no existen: $archivo_ips / $archivo_puertos" >&2
  exit 1
fi

# ================== Procesamiento ==================
# Quitamos líneas vacías y limpiamos cada valor
grep -v '^[[:space:]]*$' "$archivo_ips" | while IFS= read -r ip || [[ -n "$ip" ]]; do
  ip=$(sanitize_field "$ip")
  [[ -z "$ip" ]] && continue

  # ---- Ping con timeout portátil ----
  if run_with_timeout "$PING_TIMEOUT" ping -c 1 "$ip" >/dev/null 2>&1; then
    estado_ping="Exitoso"
  else
    estado_ping="Fallido"
  fi

  # Resultado de ping
  printf "%s,%s,%s,%s,%s,ping,N/A,%s\n" \
    "$hostname_actual" "$ip_local" "$mask" "$gateway" "$ip" "$estado_ping" >> "$archivo_salida"

  # ---- Validar puertos ----
  grep -v '^[[:space:]]*$' "$archivo_puertos" | while IFS= read -r port || [[ -n "$port" ]]; do
    port=$(sanitize_field "$port")
    [[ -z "$port" ]] && continue

    if command -v nc >/dev/null 2>&1; then
      if nc -z -w"$PORT_TIMEOUT" "$ip" "$port" >/dev/null 2>&1; then
        estado_port="Abierto"
      else
        estado_port="Cerrado"
      fi

    elif command -v telnet >/dev/null 2>&1; then
      archivo_tmp=$(mktemp)
      if run_with_timeout "$TELNET_TIMEOUT" sh -c "{ echo quit | telnet \"$ip\" \"$port\"; }" &> "$archivo_tmp"; then
        if grep -qi "Connected" "$archivo_tmp"; then
          estado_port="Abierto"
        else
          estado_port="Cerrado"
        fi
      else
        estado_port="Cerrado"
      fi
      rm -f "$archivo_tmp"

    else
      estado_port="Indeterminado"
    fi

    # Resultado de puerto
    printf "%s,%s,%s,%s,%s,puerto,%s,%s\n" \
      "$hostname_actual" "$ip_local" "$mask" "$gateway" "$ip" "$port" "$estado_port" >> "$archivo_salida"
  done
done

# ================== Limpieza final del CSV ==================
# Elimina cualquier carácter no ASCII/imprimible que haya podido colarse.
# (Protege contra NBSP, BOM, ZWSP, etc.)
sed -i 's/[^[:print:]\t]//g' "$archivo_salida"

# Fin
