"""Create a short-lived development TLS certificate for this Mac's LAN address."""
import base64
import ipaddress
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
work = root / 'work/lan-tls'
work.mkdir(parents=True, exist_ok=True)
address = subprocess.check_output(['ipconfig', 'getifaddr', 'en0'], text=True).strip()
parsed = ipaddress.ip_address(address)
if not (parsed.is_private or parsed in ipaddress.ip_network('100.64.0.0/10')):
    raise SystemExit('A non-public local-network address is required.')
config = work / 'openssl.cnf'
config.write_text(f'''[req]
distinguished_name = dn
x509_extensions = extensions
prompt = no
[dn]
CN = Voice Companion Development
[extensions]
subjectAltName = IP:{address}
basicConstraints = critical,CA:TRUE
keyUsage = critical,digitalSignature,keyEncipherment,keyCertSign
extendedKeyUsage = serverAuth
''')
key = work / 'server.key'
key.touch(mode=0o600, exist_ok=True)
key.chmod(0o600)
subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-sha256', '-days', '7',
                '-config', str(config), '-keyout', str(key), '-out', str(work / 'server.pem')],
               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
der = subprocess.check_output(['openssl', 'x509', '-in', str(work / 'server.pem'), '-outform', 'DER'])
(work / 'settings.json').write_text(json.dumps({'host': address, 'certificate': base64.b64encode(der).decode()}))
print('Created seven-day LAN TLS material under ignored work/lan-tls. No system trust settings changed.')
