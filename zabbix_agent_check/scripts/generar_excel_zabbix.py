import pandas as pd
import json
from datetime import datetime
import os

with open("Salidas_Playbooks/zabbix_auditoria.json") as f:
    data = json.load(f)

df = pd.DataFrame(data)

output_file = f"Salidas_Playbooks/Reporte_Zabbix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
df.to_excel(output_file, index=False)
print(f"Archivo Excel generado: {output_file}")
