# VALIDACIÓN DE CONECTIVIDAD: PING Y PUERTOS (LINUX & WINDOWS)

Este documento describe los métodos utilizados para validar conectividad de red 
(por ICMP/ping y verificación de puertos TCP) en sistemas Linux y Windows. 

Incluye ejemplos y explicación de los comandos utilizados en cada plataforma.

---

## LINUX

### 1. Validación de Ping
- **Comando utilizado:**
  ping -c1 -W1 <IP>

- **Parámetros:**
  - `-c1`: Envía solo un paquete.
  - `-W1`: Espera un máximo de 1 segundo por la respuesta.

- **Resultado esperado:**
  - Si el host responde: "Exitoso"
  - Si no responde: "Fallido"

### 2. Validación de Puertos TCP
- **Método:** Redirección especial de Bash con `/dev/tcp/`

- **Comando utilizado:**
  timeout 1 bash -c "echo > /dev/tcp/<IP>/<PUERTO>"

- **Explicación:**
  - Intenta abrir una conexión TCP al puerto indicado.
  - `timeout 1`: Limita la espera a 1 segundo.
  - Redirección especial `/dev/tcp/` disponible en bash.

- **Resultado esperado:**
  - Si la conexión es exitosa: "Abierto"
  - Si falla o no responde: "Cerrado"

### 3. Salida
- Se genera un archivo CSV con las siguientes columnas:
  - Nombre del host local
  - IP local
  - Máscara de red (convertida desde CIDR)
  - Gateway predeterminado
  - IP destino
  - Tipo de prueba (ping o puerto)
  - Puerto (si aplica)
  - Resultado (Exitoso, Fallido, Abierto, Cerrado)

---

## WINDOWS

### 1. Validación de Ping
- **Comando utilizado:**
  Test-Connection -ComputerName <IP> -Count 1 -Quiet

- **Parámetros:**
  - `-Count 1`: Envía solo un paquete ICMP.
  - `-Quiet`: Devuelve True/False como salida lógica.

- **Resultado esperado:**
  - True  → "Exitoso"
  - False → "Fallido"

### 2. Validación de Puertos TCP

#### Opción 1: PowerShell moderno (Windows 8 / 2012+)
- **Comando:**
  Test-NetConnection -ComputerName <IP> -Port <PUERTO>

- **Resultado esperado:**
  - `TcpTestSucceeded : True`  → Puerto Abierto
  - `TcpTestSucceeded : False` → Puerto Cerrado

#### Opción 2: PowerShell clásico
- **Comando:**
  $tcp = New-Object System.Net.Sockets.TcpClient  
  $result = $tcp.ConnectAsync("<IP>", <PUERTO>).Wait(1000)

- **Explicación:**
  - Espera hasta 1 segundo por conexión TCP.
  - Retorna `True` si logra conectarse, `False` si no.

---

## COMPARATIVA RÁPIDA

| Sistema   | Método Ping                  | Método Puerto TCP                            |
|-----------|------------------------------|-----------------------------------------------|
| Linux     | `ping -c1 -W1 <IP>`          | `timeout 1 bash -c "echo > /dev/tcp/IP/PORT"` |
| Windows   | `Test-Connection`            | `Test-NetConnection` o `TcpClient.ConnectAsync` |

---

## OBSERVACIONES

- La validación de puertos en Linux requiere bash y soporte de `/dev/tcp/`.
- En Windows se recomienda `Test-NetConnection` para versiones modernas.
- Ambos scripts (`valida_red.sh`, `valida_red.ps1`) pueden adaptarse para ambientes automatizados, incluyendo salida a CSV para informes.

