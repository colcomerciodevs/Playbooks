# 📂 Archivos de entrada y salida
$archivo_ips     = "C:\temp\archivo_ips.txt"
$archivo_puertos = "C:\temp\archivo_puertos.txt"
$archivo_salida  = "C:\temp\salida_valida_red.csv"

# 🧹 Eliminar salida anterior (si existe)
Remove-Item -Path $archivo_salida -Force -ErrorAction SilentlyContinue

# 🖥️ Información del sistema
$hostname = $env:COMPUTERNAME

$netInfo = Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
    $_.PrefixOrigin -ne "WellKnown" -and $_.IPAddress -notlike "169.254*"
} | Select-Object -First 1

$ip   = $netInfo.IPAddress
$mask = $netInfo.PrefixLength
$gw   = (Get-NetRoute -DestinationPrefix "0.0.0.0/0" | Sort-Object RouteMetric | Select-Object -First 1).NextHop

# ✅ Validar que los archivos existan
if (!(Test-Path $archivo_ips) -or !(Test-Path $archivo_puertos)) {
    "ERROR: Archivos no encontrados" | Out-File -FilePath $archivo_salida -Encoding ascii
    exit 1
}

# 🔁 Validar IPs
Get-Content $archivo_ips | Where-Object { $_.Trim() -ne "" } | ForEach-Object {
    $destino = $_.Trim()

    # 🟢 Ping
    $estado_ping = if (Test-Connection -ComputerName $destino -Count 1 -Quiet -ErrorAction SilentlyContinue) {
        "Exitoso"
    } else {
        "Fallido"
    }

    "$hostname,$ip,$mask,$gw,$destino,ping,N/A,$estado_ping" | Out-File -FilePath $archivo_salida -Append -Encoding ascii

    # 🔁 Validar puertos
    Get-Content $archivo_puertos | Where-Object { $_.Trim() -ne "" } | ForEach-Object {
        $puerto = $_.Trim()
        try {
            $tcp = New-Object System.Net.Sockets.TcpClient
            $async = $tcp.BeginConnect($destino, [int]$puerto, $null, $null)
            $success = $async.AsyncWaitHandle.WaitOne(1000, $false)
            if ($success) {
                $tcp.EndConnect($async)
                $estado_port = "Abierto"
            } else {
                $estado_port = "Cerrado"
            }
            $tcp.Close()
        } catch {
            $estado_port = "Cerrado"
        }
        "$hostname,$ip,$mask,$gw,$destino,puerto,$puerto,$estado_port"  | Out-File -FilePath $archivo_salida -Append -Encoding ascii
    }
}
