import winrm

session = winrm.Session(
    target='10.181.3.157',
    auth=('COLOMBIANA\\1026278709', 'Bogotacorbe2025*'),
    transport='ntlm',
    server_cert_validation='ignore'

)

try:
    result = session.run_cmd('hostname')
    print("✔️ Conexión exitosa.")
    print("Salida:")
    print(result.std_out.decode())
except Exception as e:
    print("❌ Error al conectar:")
    print(str(e))
