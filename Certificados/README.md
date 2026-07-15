# Generación de CSR con Ansible

## Requisitos

- Ansible Core
- OpenSSL
- Colección community.crypto

```bash
ansible-galaxy collection install community.crypto
```

## Archivos

```
README.md
generar_csr.yml
vars.yml
```

El archivo `vars.yml` contiene la información fija de la organización.

Los únicos datos que deben suministrarse en cada ejecución son:

- CN (Common Name)
- SAN (Subject Alternative Name)

## Ejecución

```bash
ansible-playbook generar_csr.yml \
-e "cn=www.ktronix.com" \
-e "san=DNS:www.ktronix.com,DNS:ktronix.com"
```

Otro ejemplo:

```bash
ansible-playbook generar_csr.yml \
-e "cn=portal.empresa.com" \
-e "san=DNS:portal.empresa.com,DNS:empresa.com,DNS:api.empresa.com"
```

## Archivos generados

```
/root/certificados/cert_2026/

www.ktronix.com.key
www.ktronix.com.csr
```

## Validación

```bash
openssl req -in /root/certificados/cert_2026/www.ktronix.com.csr -noout -text
```