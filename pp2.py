import os
import re
import sys
import ipaddress
import requests
import base64
import json
import socket
import threading
import time
import urllib.parse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Set, List, Tuple, Optional

# Отключаем предупреждения
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Попытка импорта yaml для Clash
try:
    import yaml
except ImportError:
    yaml = None

# Попытка импорта maxminddb
try:
    import maxminddb
    HAS_MAXMIND = True
except ImportError:
    HAS_MAXMIND = False
    maxminddb = None

# ===================== ИСТОЧНИКИ (РАЗДЕЛЁННЫЕ ПО ТИПАМ) =====================
SOURCES_MAIN = [
    "https://sub.vlessfo.ru/vlessforu/working_configs.txt",
    "https://n2wfe.burmaldavpn.online/EfT-CvVJdCYBa7dd",
    "https://raw.githubusercontent.com/ksenkovsolo/HardVPN-bypass-WhiteLists-/refs/heads/main/vpn-lte/WHITELIST-ALL.txt",
    "https://raw.githubusercontent.com/prominbro/sub/refs/heads/main/212.txt",
    "https://gist.githubusercontent.com/LIKE-FURRY/ea91d3f11eb50e849c6007754417dc59/raw/d40546055dd1b382d3a2e4f6f810b68d9406cacf/GothicVPNFree-iz-githab",
    "https://raw.githubusercontent.com/xolirx/list-check/main/subs/6788436831_lte.txt?v=1786267086",
    "https://raw.githubusercontent.com/xolirx/list-check/main/subs/6788436831_black.txt?v=1786267051",
    "https://short-url.cc/Shishanivpn1",
    "https://gist.githubusercontent.com/sori99346-cyber/bd11c98ceecbee68bf8aa7452a10068a/raw/49bcade516dc30646fca8eb12e902493920114c9/vpn.txt",
    "https://gist.githubusercontent.com/sori99346-cyber/683e002b7255b1da0c9c5204272bfeab/raw/9ad935bd17429ed21a020f40d5180a23bc5f45c2/vpn.txt",
    "https://gist.githubusercontent.com/sori99346-cyber/ed70bd2f52b04ce73a578f6ed90f7952/raw/9edc274426f05c534f2f1b553989fbb4d862f88c/happ.txt",
    "https://gist.githubusercontent.com/sori99346-cyber/ddb62003fb73adc734c772aa1d9588e6/raw/2c96bdd9077b8bd48c8006af3ec328994709d9a9/happ.txt",
    "https://gist.githubusercontent.com/sori99346-cyber/81672bad6e3fcf8f4ba7dc5c94dd5d2d/raw/de8193dafbbd016b7d96222d77764592ec532570/@ConfigiHapp.txt",
    "https://ru-sub.whit3.net/sub/_wW4Z5cBRB4d6ypL",
    "https://sub.aska.lol/free",
    "https://sub.aska.lol/Ux7lmK0xkIl2",
    "https://gist.githubusercontent.com/Semenhach1/49b3bdf4e07c64d28b7c79ee185ecb3b/raw/r_8742354695.txt#?hwidlink=ku96hegl2vxp3vgl",
    "https://gist.githubusercontent.com/LIKE-FURRY/af64b3ca475a5a66f0a47c1e07038fd5/raw/@FURRY_VPN_FREE-PREMIUM-CLUCHI-FILTR-IZ-GITHAB",
    "https://raw.githubusercontent.com/LimeHi/LimeVPN/refs/heads/main/whitelist.txt",
    "https://raw.githubusercontent.com/LimeHi/LimeVPN/refs/heads/main/blacklist.txt",
    "https://raw.githubusercontent.com/shabane/kamaji/master/hub/merged.txt",
    "https://github.com/FLAT447/v2ray-lists/raw/refs/heads/main/BLACK_FULL.txt",
    "https://github.com/FLAT447/v2ray-lists/raw/refs/heads/main/WHITE_FULL.txt",
    "https://raw.githubusercontent.com/ebrasha/free-v2ray-public-list/refs/heads/main/V2Ray-Config-By-EbraSha-All-Type.txt",
    "https://alley.serv00.net/whitelist",
    "https://alley.serv00.net/other",
    "https://alley.serv00.net/youtube",
    "https://gitverse.ru/api/repos/RKP_channel/RKP_bypass_configs/raw/branch/master/whitelist.txt",
    "https://raw.githubusercontent.com/RKPchannel/RKP_bypass_configs/refs/heads/main/blacklist.txt",
    "https://subrostunnel.vercel.app/gen.txt",
    "https://rostunnel.vercel.app/mega.txt",
]

SOURCES_HAPP_CRYPT = []
SOURCES_INCY_CRYPT = []
SOURCES_HAPP_ADD = []
SOURCES_INCY_ADD = []

SOURCES = SOURCES_MAIN + SOURCES_HAPP_CRYPT + SOURCES_INCY_CRYPT + SOURCES_HAPP_ADD + SOURCES_INCY_ADD

# ===================== НАСТРОЙКИ =====================
CHECK_TIMEOUT = 15
TOP_LIMIT = 150          # для Happ
LIMIT = 1000             # для основного и Clash файлов

# ===================== НАСТРОЙКИ ПОТОКОВ =====================
LOAD_THREADS = 100        # потоки для загрузки источников
CHECK_THREADS = 100000    # потоки для проверки конфигов
COUNTRY_THREADS = 100000  # потоки для определения страны (ВОЗВРАЩЕНЫ)

CONFIG_FILE_ALL = "MiltaryVPN.txt"
CONFIG_FILE_HAPP = "MiltaryVPN_Happ.txt"
CONFIG_FILE_CLASH = "MiltaryVPN.yaml"
PROFILE_TITLE_ALL = "Miltary VPN - несколько VPN в один VPN."
PROFILE_TITLE_HAPP = "Miltary VPN - несколько VPN в один VPN. | 🔑 Оптимизированно для Happ"
PROFILE_TITLE_CLASH = "Miltary VPN - несколько VPN в один VPN. | 🔑 Для Clash/Mihomo"
SUPPORT_URL = "https://t.me/MiltaryVPN"

LOG_FILE = "log.csv"
BASE_DIR = os.path.abspath(os.getcwd())
TEMP_DIR = "temp"
SOURCES_DIR = "sources"

# MaxMind DB
MAXMIND_DB_URL = "https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-Country.mmdb"
MAXMIND_DB_PATH = os.path.join(TEMP_DIR, "GeoLite2-Country.mmdb")
_maxmind_reader = None

# User-Agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Happ/3.26.0/Android/17771400994551771562",
    "Incy/2.0.0/Android",
    "v2raytun/1.0.0"
]

# ============================================================
#  MAXMIND DB
# ============================================================
def download_maxmind_db():
    if os.path.exists(MAXMIND_DB_PATH):
        return MAXMIND_DB_PATH
    sys.stdout.write("Скачивание GeoLite2-Country.mmdb...\n")
    try:
        resp = requests.get(MAXMIND_DB_URL, timeout=120, stream=True)
        if resp.status_code == 200:
            total = int(resp.headers.get('content-length', 0))
            downloaded = 0
            with open(MAXMIND_DB_PATH, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = downloaded / total
                        filled = int(30 * pct)
                        bar = "█" * filled + "░" * (30 - filled)
                        sys.stdout.write(f"\rЗагрузка DB |{bar}| {pct*100:.0f}%")
                        sys.stdout.flush()
            sys.stdout.write('\n')
            sys.stdout.write("База MaxMind сохранена.\n")
            return MAXMIND_DB_PATH
        else:
            sys.stdout.write(f"Ошибка загрузки DB: HTTP {resp.status_code}\n")
    except Exception as e:
        sys.stdout.write(f"Ошибка загрузки DB: {e}\n")
    return None

def get_country_via_maxmind(ip: str) -> Optional[Tuple[str, str]]:
    if not HAS_MAXMIND or not _maxmind_reader:
        return None
    try:
        result = _maxmind_reader.get(ip)
        if result and 'country' in result:
            country = result['country']
            code = country.get('iso_code', '')
            names = country.get('names', {})
            name = names.get('ru', names.get('en', ''))
            if code and name:
                return (name, code)
    except:
        pass
    return None

# ============================================================
#  ПАРСИНГ ИЗВЛЕЧЕНИЕ КОНФИГОВ
# ============================================================
VLESS_REGEX = re.compile(r"vless://[^\s#]+", re.IGNORECASE)
TROJAN_REGEX = re.compile(r"trojan://[^\s#]+", re.IGNORECASE)
HY2_REGEX = re.compile(r"(?:hysteria2|hy2)://[^\s#]+", re.IGNORECASE)
VMESS_REGEX = re.compile(r"vmess://[^\s#]+", re.IGNORECASE)
SS_REGEX = re.compile(r"ss://[^\s#]+", re.IGNORECASE)
SSR_REGEX = re.compile(r"ssr://[^\s#]+", re.IGNORECASE)
BASE64_REGEX = re.compile(r'^[A-Za-z0-9+/]+=*$', re.MULTILINE)

def decode_base64_content(content: str) -> Tuple[Optional[str], List[str]]:
    try:
        content = content.strip()
        if not BASE64_REGEX.match(content.replace('\n', '').replace('\r', '')):
            return None, []
        decoded = base64.b64decode(content).decode('utf-8', errors='ignore')
        matches = []
        matches.extend(VLESS_REGEX.findall(decoded))
        matches.extend(TROJAN_REGEX.findall(decoded))
        matches.extend(HY2_REGEX.findall(decoded))
        matches.extend(VMESS_REGEX.findall(decoded))
        matches.extend(SS_REGEX.findall(decoded))
        matches.extend(SSR_REGEX.findall(decoded))
        if len(decoded) > 100 and BASE64_REGEX.match(decoded.replace('\n', '').replace('\r', '')):
            deeper = decode_base64_content(decoded)
            if deeper[1]:
                matches.extend(deeper[1])
        return decoded, matches
    except:
        return None, []

def outbound_to_vless_url(out: dict) -> Optional[str]:
    try:
        settings = out.get('settings', {})
        vnext = settings.get('vnext', [])
        if not vnext:
            return None
        first = vnext[0]
        address = first.get('address')
        port = first.get('port')
        users = first.get('users', [])
        if not users:
            return None
        user = users[0]
        uuid = user.get('id')
        if not uuid:
            return None
        encryption = user.get('encryption', 'none')
        flow = user.get('flow', '')
        stream = out.get('streamSettings', {})
        network = stream.get('network', 'tcp')
        security = stream.get('security', '')
        params = {}
        if encryption and encryption != 'none':
            params['encryption'] = encryption
        if network != 'tcp':
            params['type'] = network
        if flow:
            params['flow'] = flow
        if security == 'reality':
            params['security'] = 'reality'
            reality = stream.get('realitySettings', {})
            if 'serverName' in reality:
                params['sni'] = reality['serverName']
            if 'publicKey' in reality:
                params['pbk'] = reality['publicKey']
            if 'shortId' in reality:
                params['sid'] = reality['shortId']
            if 'fingerprint' in reality:
                params['fp'] = reality['fingerprint']
        elif security == 'tls':
            params['security'] = 'tls'
            tls = stream.get('tlsSettings', {})
            if 'serverName' in tls:
                params['sni'] = tls['serverName']
            if 'allowInsecure' in tls:
                params['allowInsecure'] = '1' if tls['allowInsecure'] else '0'
            if 'fingerprint' in tls:
                params['fp'] = tls['fingerprint']
        query = '&'.join(f"{k}={urllib.parse.quote(str(v), safe='')}" for k, v in params.items() if v)
        return f"vless://{uuid}@{address}:{port}?{query}"
    except:
        return None

def outbound_to_trojan_url(out: dict) -> Optional[str]:
    try:
        settings = out.get('settings', {})
        servers = settings.get('servers', [])
        if not servers:
            return None
        s = servers[0]
        address = s.get('address')
        port = s.get('port')
        password = s.get('password')
        if not all([address, port, password]):
            return None
        stream = out.get('streamSettings', {})
        security = stream.get('security', 'tls')
        params = {}
        if security == 'tls':
            tls = stream.get('tlsSettings', {})
            if 'serverName' in tls:
                params['sni'] = tls['serverName']
            if 'allowInsecure' in tls:
                params['allowInsecure'] = '1' if tls['allowInsecure'] else '0'
            if 'fingerprint' in tls:
                params['fp'] = tls['fingerprint']
        query = '&'.join(f"{k}={urllib.parse.quote(str(v), safe='')}" for k, v in params.items() if v)
        base = f"trojan://{password}@{address}:{port}"
        if query:
            base += f"?{query}"
        return base
    except:
        return None

def convert_json_to_urls(content: str) -> List[str]:
    urls = []
    try:
        decoder = json.JSONDecoder()
        idx = 0
        content = content.strip()
        while idx < len(content):
            try:
                obj, end = decoder.raw_decode(content, idx)
                idx = end
                while idx < len(content) and content[idx] in ' \t\n\r':
                    idx += 1
                outbounds = None
                if isinstance(obj, dict):
                    outbounds = obj.get('outbounds')
                    if outbounds is None and 'config' in obj:
                        outbounds = obj['config'].get('outbounds')
                elif isinstance(obj, list):
                    outbounds = obj
                if not outbounds or not isinstance(outbounds, list):
                    continue
                for out in outbounds:
                    if not isinstance(out, dict):
                        continue
                    protocol = out.get('protocol', '')
                    if protocol == 'vless':
                        url = outbound_to_vless_url(out)
                        if url:
                            urls.append(url)
                    elif protocol == 'trojan':
                        url = outbound_to_trojan_url(out)
                        if url:
                            urls.append(url)
            except json.JSONDecodeError:
                break
    except:
        pass
    return urls

def yaml_proxy_to_vless_url(proxy: dict) -> Optional[str]:
    try:
        server = proxy.get('server')
        port = proxy.get('port')
        uuid = proxy.get('uuid')
        if not all([server, port, uuid]):
            return None
        params = {'encryption': 'none', 'type': proxy.get('network', 'tcp')}
        if proxy.get('flow'):
            params['flow'] = proxy['flow']
        tls = proxy.get('tls', False)
        reality_opts = proxy.get('reality-opts', {})
        if reality_opts:
            params['security'] = 'reality'
            if 'public-key' in reality_opts:
                params['pbk'] = reality_opts['public-key']
            if 'short-id' in reality_opts:
                params['sid'] = reality_opts['short-id']
        elif tls:
            params['security'] = 'tls'
        sni = proxy.get('servername')
        if sni:
            params['sni'] = sni
        fp = proxy.get('client-fingerprint')
        if fp:
            params['fp'] = fp
        network = proxy.get('network', 'tcp')
        if network == 'grpc':
            grpc_opts = proxy.get('grpc-opts', {})
            if 'grpc-service-name' in grpc_opts:
                params['serviceName'] = grpc_opts['grpc-service-name']
        elif network in ('ws', 'websocket'):
            ws_opts = proxy.get('ws-opts', {})
            if 'path' in ws_opts:
                params['path'] = ws_opts['path']
            if 'headers' in ws_opts and 'Host' in ws_opts['headers']:
                params['host'] = ws_opts['headers']['Host']
        query = '&'.join(f"{k}={urllib.parse.quote(str(v), safe='')}" for k, v in params.items() if v)
        return f"vless://{uuid}@{server}:{port}?{query}"
    except:
        return None

def yaml_proxy_to_trojan_url(proxy: dict) -> Optional[str]:
    try:
        server = proxy.get('server')
        port = proxy.get('port')
        password = proxy.get('password')
        if not all([server, port, password]):
            return None
        params = {}
        sni = proxy.get('servername')
        if sni:
            params['sni'] = sni
        tls = proxy.get('tls', False)
        if tls:
            params['security'] = 'tls'
        fp = proxy.get('client-fingerprint')
        if fp:
            params['fp'] = fp
        query = '&'.join(f"{k}={urllib.parse.quote(str(v), safe='')}" for k, v in params.items() if v)
        base = f"trojan://{password}@{server}:{port}"
        if query:
            base += f"?{query}"
        return base
    except:
        return None

def convert_yaml_to_urls(content: str) -> List[str]:
    if yaml is None:
        return []
    urls = []
    try:
        data = yaml.safe_load(content)
        if not data or not isinstance(data, dict):
            return []
        proxies = data.get('proxies', [])
        if not isinstance(proxies, list):
            return []
        for proxy in proxies:
            ptype = proxy.get('type')
            if ptype == 'vless':
                url = yaml_proxy_to_vless_url(proxy)
            elif ptype == 'trojan':
                url = yaml_proxy_to_trojan_url(proxy)
            else:
                continue
            if url:
                urls.append(url)
    except:
        pass
    return urls

def extract_configs_from_text(text: str) -> List[str]:
    configs = []
    configs.extend(VLESS_REGEX.findall(text))
    configs.extend(TROJAN_REGEX.findall(text))
    configs.extend(HY2_REGEX.findall(text))
    configs.extend(VMESS_REGEX.findall(text))
    configs.extend(SS_REGEX.findall(text))
    configs.extend(SSR_REGEX.findall(text))
    b64_res = decode_base64_content(text)
    if b64_res[1]:
        configs.extend(b64_res[1])
    if text.strip().startswith(('{', '[')):
        json_urls = convert_json_to_urls(text)
        configs.extend(json_urls)
    if yaml is not None and ('proxies:' in text or 'type: vless' in text.lower()):
        yaml_urls = convert_yaml_to_urls(text)
        configs.extend(yaml_urls)
    return configs

# ============================================================
#  ДЕДУПЛИКАЦИЯ И ПАРСИНГ URL
# ============================================================
def extract_sni_from_url(url: str) -> str:
    m = re.search(r'[?&](?:sni|host)=([^&#]+)', url, re.IGNORECASE)
    if m:
        return urllib.parse.unquote(m.group(1))
    return ""

def parse_host_port(url: str) -> Optional[Tuple[str, int]]:
    m = re.search(r'@([^:]+):(\d+)', url)
    if m:
        return (m.group(1), int(m.group(2)))
    if url.startswith("vmess://"):
        try:
            b64 = url[8:].split('#')[0].split('?')[0]
            b64 += '=' * (4 - len(b64) % 4) if len(b64) % 4 else ''
            decoded = base64.b64decode(b64).decode('utf-8', errors='ignore')
            data = json.loads(decoded)
            host = data.get('add')
            port = data.get('port')
            if host and port:
                return (host, int(port))
        except:
            pass
    if url.startswith("ss://"):
        try:
            b64_part = url[5:].split('#')[0].split('?')[0]
            b64_part += '=' * (4 - len(b64_part) % 4) if len(b64_part) % 4 else ''
            decoded = base64.b64decode(b64_part).decode('utf-8', errors='ignore')
            if '@' in decoded:
                _, host_port = decoded.split('@', 1)
                if ':' in host_port:
                    host, port_str = host_port.rsplit(':', 1)
                    if port_str.isdigit():
                        return (host, int(port_str))
        except:
            pass
        m2 = re.search(r'ss://[^@]+@([^:]+):(\d+)', url)
        if m2:
            return (m2.group(1), int(m2.group(2)))
    if url.startswith("ssr://"):
        try:
            b64 = url[6:].split('#')[0].split('?')[0]
            b64 += '=' * (4 - len(b64) % 4) if len(b64) % 4 else ''
            decoded = base64.b64decode(b64).decode('utf-8', errors='ignore')
            parts = decoded.split(':')
            if len(parts) >= 6:
                host = parts[0]
                port = int(parts[1])
                return (host, port)
        except:
            pass
    return None

VLESS_REGEX_DEDUP = re.compile(r"vless://([^@]+)@([^:]+):(\d+)", re.IGNORECASE)
TROJAN_REGEX_DEDUP = re.compile(r"trojan://([^@]+)@([^:]+):(\d+)", re.IGNORECASE)
HY2_REGEX_DEDUP = re.compile(r"(?:hysteria2|hy2)://(?:([^@]+)@)?([^:]+):(\d+)", re.IGNORECASE)

def extract_vless_key(url: str) -> Optional[Tuple[str, str, int, str]]:
    match = VLESS_REGEX_DEDUP.search(url)
    if not match:
        return None
    uuid = match.group(1)
    host = match.group(2)
    port = int(match.group(3))
    sni = extract_sni_from_url(url)
    return (uuid, host, port, sni)

def extract_trojan_key(url: str) -> Optional[Tuple[str, str, int, str]]:
    match = TROJAN_REGEX_DEDUP.search(url)
    if not match:
        return None
    password = urllib.parse.unquote(match.group(1))
    host = match.group(2)
    port = int(match.group(3))
    sni = extract_sni_from_url(url)
    return (password, host, port, sni)

def extract_hy2_key(url: str) -> Optional[Tuple[str, str, int, str]]:
    match = HY2_REGEX_DEDUP.search(url)
    if not match:
        return None
    auth = urllib.parse.unquote(match.group(1)) if match.group(1) else ""
    host = match.group(2)
    port = int(match.group(3))
    sni = extract_sni_from_url(url)
    return (auth, host, port, sni)

def get_config_key(url: str) -> Optional[Tuple[str, str, str, int, str]]:
    if url.startswith("vless://"):
        key = extract_vless_key(url)
        if key:
            return ("vless", key[0], key[1], key[2], key[3])
    elif url.startswith("trojan://"):
        key = extract_trojan_key(url)
        if key:
            return ("trojan", key[0], key[1], key[2], key[3])
    elif url.startswith(("hysteria2://", "hy2://")):
        key = extract_hy2_key(url)
        if key:
            return ("hy2", key[0], key[1], key[2], key[3])
    elif url.startswith("vmess://"):
        hp = parse_host_port(url)
        if hp:
            return ("vmess", "", hp[0], hp[1], "")
    elif url.startswith("ss://"):
        hp = parse_host_port(url)
        if hp:
            return ("ss", "", hp[0], hp[1], "")
    elif url.startswith("ssr://"):
        hp = parse_host_port(url)
        if hp:
            return ("ssr", "", hp[0], hp[1], "")
    return None

def normalize_config(url: str) -> str:
    try:
        if "#" in url:
            url = url.split("#", 1)[0]
        if "?" in url:
            base, query = url.split("?", 1)
            params = {}
            for p in query.split("&"):
                if "=" in p:
                    k, v = p.split("=", 1)
                    params[k] = v
                else:
                    params[p] = ""
            sorted_params = sorted(params.items())
            new_query = "&".join(f"{k}={v}" for k, v in sorted_params)
            url = f"{base}?{new_query}"
        return url
    except:
        return url

# ============================================================
#  ИСПРАВЛЕНИЕ GITHUB ССЫЛОК
# ============================================================
_GITHUB_RAW_RE = re.compile(r"^https://raw\.githubusercontent\.com/([^/]+)/([^/]+)/([a-f0-9]{40})(/.*)$", re.IGNORECASE)

def fix_github_url(url: str) -> str:
    m = _GITHUB_RAW_RE.match(url)
    if not m:
        return url
    user, repo, _sha, path = m.group(1), m.group(2), m.group(3), m.group(4)
    for branch in ("main", "master"):
        fixed = f"https://raw.githubusercontent.com/{user}/{repo}/{branch}{path}"
        try:
            r = requests.head(fixed, timeout=5, verify=False)
            if r.status_code == 200:
                return fixed
        except:
            continue
    return url

# ============================================================
#  РАСШИФРОВКА HAPP/INCY CRYPT И ADD
# ============================================================
def decrypt_happ_crypt(link: str) -> Optional[str]:
    try:
        resp = requests.post(
            "https://api.ioo.ir/v1/happ/decrypt",
            json={"link": link},
            timeout=15
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("url")
    except:
        pass
    return None

def decrypt_incy_crypt(link: str) -> Optional[str]:
    try:
        resp = requests.post(
            "https://api.ioo.ir/v1/incy/decrypt",
            json={"link": link},
            timeout=15
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("url")
    except:
        pass
    return None

def extract_url_from_add(link: str) -> Optional[str]:
    if link.startswith(("happ://add/", "incy://add/")):
        url_part = link.split("add/", 1)[1]
        if url_part.startswith("http://") or url_part.startswith("https://"):
            return url_part
    return None

# ============================================================
#  ЗАГРУЗКА С ПЕРЕБОРОМ USER-AGENT
# ============================================================
def load_with_ua(url: str, timeout: int = 15) -> Tuple[Optional[str], List[str]]:
    best_content = None
    best_configs = []
    for ua in USER_AGENTS:
        try:
            headers = {"User-Agent": ua}
            resp = requests.get(url, timeout=(5, timeout), headers=headers, verify=False)
            if resp.status_code != 200:
                continue
            content = resp.text
            if not content or len(content) < 10:
                continue
            configs = extract_configs_from_text(content)
            if len(configs) > len(best_configs):
                best_configs = configs
                best_content = content
        except:
            continue
    if best_content is None:
        # fallback
        content = fetch_with_happ_method(url)
        if content:
            configs = extract_configs_from_text(content)
            if configs:
                return content, configs
        return None, []
    return best_content, best_configs

def fetch_with_happ_method(url: str) -> Optional[str]:
    HWID_STATIC = "d060e73eb61d1ba7"
    HAPP_USER_AGENTS = ["Happ/3.26.0/Android/17771400994551771562"]
    parsed = urllib.parse.urlparse(url)
    if 'hwid=' not in url:
        sep = '&' if parsed.query else '?'
        url_with_hwid = f"{url}{sep}hwid={HWID_STATIC}"
    else:
        url_with_hwid = url
    for try_url in (url_with_hwid, url):
        for ua in HAPP_USER_AGENTS:
            try:
                headers = {
                    "User-Agent": ua,
                    "X-HWID": HWID_STATIC,
                    "Accept": "*/*",
                }
                resp = requests.get(try_url, headers=headers, timeout=8, verify=False)
                if resp.status_code == 200:
                    content = resp.text.strip()
                    if not content or "<html" in content.lower():
                        continue
                    b64_check = re.sub(r'[\r\n]', '', content)
                    if re.fullmatch(r'^[A-Za-z0-9+/]+=*$', b64_check):
                        try:
                            decoded = base64.b64decode(b64_check).decode('utf-8', errors='ignore')
                            if decoded:
                                return decoded
                        except:
                            pass
                    return content
            except:
                continue
    return None

# ============================================================
#  ПРОВЕРКА КОНФИГОВ (ТОЛЬКО TCP) И ОПРЕДЕЛЕНИЕ СТРАНЫ (ОТДЕЛЬНО)
# ============================================================
def resolve_host(host: str) -> Optional[str]:
    try:
        return socket.gethostbyname(host)
    except:
        return None

def tcp_check(host: str, port: int, timeout: int) -> Tuple[bool, Optional[float]]:
    try:
        start = time.time()
        with socket.create_connection((host, port), timeout=timeout) as sock:
            elapsed = (time.time() - start) * 1000
            return True, elapsed
    except:
        return False, None

def check_config_tcp(proxy_url: str, timeout: int) -> Tuple[Optional[str], Optional[float]]:
    """Проверяет только TCP-доступность, возвращает (url, ping) или (None, None)."""
    hp = parse_host_port(proxy_url)
    if not hp:
        return None, None
    host, port = hp
    ok, ping = tcp_check(host, port, timeout)
    if not ok:
        return None, None
    # Возвращаем исходный URL (без тега, тег добавим позже)
    return proxy_url, ping

def get_country_info(host: str) -> Optional[Tuple[str, str]]:
    """Определяет страну по IP: MaxMind → freeipapi.com → ip-api.com."""
    country = None
    code = None
    ip = host
    if not re.match(r'^\d+\.\d+\.\d+\.\d+$', ip):
        resolved = resolve_host(ip)
        if resolved:
            ip = resolved
    if ip:
        # 1. MaxMind DB
        country_info = get_country_via_maxmind(ip)
        if country_info:
            country, code = country_info
    if not country:
        # 2. freeipapi.com
        try:
            r = requests.get("https://freeipapi.com/api/json/", timeout=5)
            if r.status_code == 200:
                data = r.json()
                country = data.get('countryName', '').strip()
                code = data.get('countryCode', '').strip()
        except:
            pass
    if not country:
        # 3. ip-api.com
        try:
            r = requests.get("http://ip-api.com/json/?fields=country,countryCode&lang=ru", timeout=5)
            if r.status_code == 200:
                data = r.json()
                if data.get('status') == 'success':
                    country = data.get('country', '').strip()
                    code = data.get('countryCode', '').strip()
        except:
            pass
    if country and code:
        return (country, code)
    return None

def update_url_with_country(proxy_url: str, country_info: Optional[Tuple[str, str]]) -> str:
    flag = ""
    if country_info:
        country, code = country_info
        if len(code) == 2:
            flag = ''.join(chr(127397 + ord(c)) for c in code)
        new_tag = f"{flag} {country} | Miltary VPN"
    else:
        new_tag = "🌐 Неизвестно | Miltary VPN"
    encoded_tag = urllib.parse.quote(new_tag, safe='')
    base_url = proxy_url.split('#')[0]
    return f"{base_url}#{encoded_tag}"

# ============================================================
#  ОСНОВНАЯ ФУНКЦИЯ
# ============================================================
def main():
    global _maxmind_reader
    os.makedirs(TEMP_DIR, exist_ok=True)
    os.makedirs(SOURCES_DIR, exist_ok=True)

    db_path = download_maxmind_db()
    if db_path and HAS_MAXMIND:
        try:
            _maxmind_reader = maxminddb.open_database(db_path)
        except Exception as e:
            sys.stdout.write(f"[!] Ошибка открытия MaxMind DB: {e}\n")

    sys.stdout.write(f"🌐 Miltary VPN - сбор и проверка (TCP прямой, 4 UA) | источников: {len(SOURCES)}\n")
    sys.stdout.write(f"📡 Потоки: загрузка={LOAD_THREADS}, проверка={CHECK_THREADS}, страны={COUNTRY_THREADS}\n")
    sys.stdout.write("📡 Начало загрузки...\n")

    # Сбор сырых конфигов
    raw_configs = []
    url_set = set()
    config_keys = set()

    def add_raw_config(cfg):
        nonlocal raw_configs, url_set, config_keys
        if not any(cfg.startswith(p) for p in ('vless://', 'trojan://', 'vmess://', 'ss://', 'ssr://', 'hysteria2://', 'hy2://')):
            return
        key = get_config_key(cfg)
        if key:
            if key in config_keys:
                return
            config_keys.add(key)
        else:
            norm = normalize_config(cfg)
            if norm in url_set:
                return
            url_set.add(norm)
        raw_configs.append(cfg)

    def process_source(link):
        real_url = None
        if link.startswith("happ://crypt"):
            real_url = decrypt_happ_crypt(link)
        elif link.startswith("incy://crypt"):
            real_url = decrypt_incy_crypt(link)
        elif link.startswith(("happ://add/", "incy://add/")):
            real_url = extract_url_from_add(link)
        else:
            real_url = link

        if not real_url:
            return

        real_url = fix_github_url(real_url)
        content, configs = load_with_ua(real_url, timeout=15)

        if not configs:
            return

        for cfg in configs:
            add_raw_config(cfg)

    total = len(SOURCES)
    done = 0
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=LOAD_THREADS) as executor:
        futures = {executor.submit(process_source, src): src for src in SOURCES}
        for future in as_completed(futures):
            done += 1
            elapsed = time.time() - start_time
            speed = done / elapsed if elapsed > 0 else 0
            sys.stdout.write(f"\rЗагрузка | {done}/{total} | {speed:.1f}/сек | найдено: {len(raw_configs)}")
            sys.stdout.flush()
    sys.stdout.write('\n')
    sys.stdout.write(f"Собрано конфигов: {len(raw_configs)}\n")

    # 1. Проверка TCP (быстро, без определения страны)
    sys.stdout.write(f"🔄 Проверка конфигов (TCP прямой, таймаут: {CHECK_TIMEOUT}с, потоков: {CHECK_THREADS})...\n")
    alive = []
    with ThreadPoolExecutor(max_workers=CHECK_THREADS) as executor:
        futures = {executor.submit(check_config_tcp, cfg, CHECK_TIMEOUT): cfg for cfg in raw_configs}
        done = 0
        total_c = len(raw_configs)
        for future in as_completed(futures):
            done += 1
            sys.stdout.write(f"\rПроверка | {done}/{total_c}")
            sys.stdout.flush()
            url, ping = future.result()
            if url and ping is not None:
                alive.append((url, ping))
    sys.stdout.write('\n')
    sys.stdout.write(f"Рабочих конфигов: {len(alive)}\n")

    if not alive:
        sys.stdout.write("❌ Нет рабочих конфигов. Завершаем.\n")
        return

    # 2. Определение страны для рабочих конфигов (параллельно)
    sys.stdout.write(f"🌍 Определение стран (потоков: {COUNTRY_THREADS})...\n")
    final_configs = []
    with ThreadPoolExecutor(max_workers=COUNTRY_THREADS) as executor:
        def process_country(url_ping):
            url, ping = url_ping
            hp = parse_host_port(url)
            if hp:
                host = hp[0]
                country_info = get_country_info(host)
                new_url = update_url_with_country(url, country_info)
                return (new_url, ping)
            return (url, ping)
        futures = {executor.submit(process_country, item): item for item in alive}
        done = 0
        total_c = len(alive)
        for future in as_completed(futures):
            done += 1
            sys.stdout.write(f"\rСтраны | {done}/{total_c}")
            sys.stdout.flush()
            final_configs.append(future.result())
    sys.stdout.write('\n')
    sys.stdout.write(f"Определены страны для {len(final_configs)} конфигов\n")

    # Сортируем по пингу
    final_configs.sort(key=lambda x: x[1])
    all_working = [url for url, _ in final_configs]
    top_1000 = all_working[:LIMIT]
    top_150 = all_working[:TOP_LIMIT]

    sys.stdout.write(f"✅ Сохраняем {len(top_1000)} конфигов (лимит {LIMIT}) в основной файл и Clash, и {len(top_150)} лучших для Happ\n")

    # Основной файл (первые 1000)
    header = [
        "#profile-update-interval: 1",
        f"#support-url: {SUPPORT_URL}",
        f"#profile-title: {PROFILE_TITLE_ALL}",
        "#hide-settings: 1",
        ""
    ]
    content = '\n'.join(header) + '\n'
    for url in top_1000:
        content += url + '\n'
    with open(CONFIG_FILE_ALL, 'w', encoding='utf-8') as f:
        f.write(content)
    sys.stdout.write(f"✅ Сохранено {len(top_1000)} конфигов в {CONFIG_FILE_ALL}\n")

    # Файл для Happ (топ-150)
    header_happ = [
        "#profile-update-interval: 1",
        f"#support-url: {SUPPORT_URL}",
        f"#profile-title: {PROFILE_TITLE_HAPP}",
        "#hide-settings: 1",
        ""
    ]
    content_happ = '\n'.join(header_happ) + '\n'
    for url in top_150:
        content_happ += url + '\n'
    with open(CONFIG_FILE_HAPP, 'w', encoding='utf-8') as f:
        f.write(content_happ)
    sys.stdout.write(f"✅ Сохранено {len(top_150)} самых быстрых конфигов в {CONFIG_FILE_HAPP}\n")

    # Clash YAML (первые 1000)
    if yaml is not None:
        sys.stdout.write("Генерация Clash YAML...\n")
        clash_proxies = []
        for url in top_1000:
            p = parse_config_url(url)
            if p:
                cp = parsed_to_clash_proxy(p)
                if cp:
                    clash_proxies.append(cp)
        if clash_proxies:
            clash_config = generate_clash_config(clash_proxies)
            yaml_content = yaml.dump(clash_config, allow_unicode=True, default_flow_style=False, sort_keys=False)
            header_clash = f"#profile-title: {PROFILE_TITLE_CLASH}\n#support-url: {SUPPORT_URL}\n"
            with open(CONFIG_FILE_CLASH, 'w', encoding='utf-8') as f:
                f.write(header_clash + yaml_content)
            sys.stdout.write(f"✅ Сохранено {len(clash_proxies)} прокси в {CONFIG_FILE_CLASH}\n")
        else:
            sys.stdout.write("⚠️ Не удалось сгенерировать Clash YAML\n")
    else:
        sys.stdout.write("⚠️ PyYAML не установлен. Clash YAML не создан.\n")

    # Лог
    log_path = os.path.join(BASE_DIR, LOG_FILE)
    needed_header = not os.path.exists(log_path)
    with open(log_path, 'a', encoding='utf-8') as f:
        if needed_header:
            f.write("timestamp,total_working,top_count\n")
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')},{len(top_1000)},{len(top_150)}\n")

    sys.stdout.write(f"📁 Результаты сохранены в корень: {BASE_DIR}\n")

# ============================================================
#  Clash-функции (vless, trojan, vmess, ss, hysteria2)
# ============================================================
def parse_config_url(url: str) -> Optional[dict]:
    if url.startswith("vless://"):
        return parse_vless(url)
    elif url.startswith("trojan://"):
        return parse_trojan(url)
    elif url.startswith("vmess://"):
        return parse_vmess(url)
    elif url.startswith("ss://"):
        return parse_ss(url)
    elif url.startswith(("hysteria2://", "hy2://")):
        return parse_hysteria2(url)
    else:
        return None

def parse_vless(url: str) -> Optional[dict]:
    try:
        url = url.strip()
        if '#' in url:
            parts = url.split('#', 1)
            main_part = parts[0]
            tag = urllib.parse.unquote(parts[1]).strip()
        else:
            main_part = url
            tag = "vless"
        match = re.search(r'vless://([^@]+)@([^:]+):(\d+)', main_part)
        if not match:
            return None
        uuid = match.group(1).strip()
        address = match.group(2).strip()
        port = int(match.group(3))
        params = {}
        if '?' in main_part:
            query = main_part.split('?', 1)[1]
            params = urllib.parse.parse_qs(query)
        def get_p(key, default=""):
            val = params.get(key, [default])
            return val[0].strip() if val[0] else default
        net_type = get_p("type", "tcp").lower()
        security = get_p("security", "none").lower()
        if security == "tls" and get_p("pbk", ""):
            security = "reality"
        return {
            "protocol": "vless",
            "uuid": uuid,
            "address": address,
            "port": port,
            "type": net_type,
            "security": security,
            "path": urllib.parse.unquote(get_p("path", "")),
            "host": get_p("host", ""),
            "sni": get_p("sni", ""),
            "fp": get_p("fp", "chrome"),
            "alpn": get_p("alpn", ""),
            "serviceName": get_p("serviceName", ""),
            "flow": get_p("flow", "xtls-rprx-vision"),
            "pbk": get_p("pbk", ""),
            "sid": get_p("sid", ""),
            "allowInsecure": get_p("allowInsecure", "true").lower() in ("true", "1", "yes"),
            "tag": tag
        }
    except:
        return None

def parse_trojan(url: str) -> Optional[dict]:
    try:
        url = url.strip()
        if '#' in url:
            url_clean, tag = url.split('#', 1)
            tag = urllib.parse.unquote(tag).strip()
        else:
            url_clean = url
            tag = "trojan"
        parsed = urllib.parse.urlparse(url_clean)
        query_params = urllib.parse.parse_qs(parsed.query)
        password = urllib.parse.unquote(parsed.username or "trojan")
        def get_q(key, default=""):
            val = query_params.get(key, [default])
            return urllib.parse.unquote(val[0].strip()) if val[0] else default
        net_type = get_q("type", "tcp").lower()
        security = get_q("security", "tls").lower()
        return {
            "protocol": "trojan",
            "password": password,
            "address": parsed.hostname,
            "port": int(parsed.port or 443),
            "type": net_type,
            "security": security,
            "path": get_q("path", ""),
            "host": get_q("host", ""),
            "sni": get_q("sni", ""),
            "fp": get_q("fp", "chrome"),
            "alpn": get_q("alpn", ""),
            "serviceName": get_q("serviceName", ""),
            "allowInsecure": get_q("allowInsecure", "true").lower() in ("true", "1", "yes"),
            "tag": tag
        }
    except:
        return None

def parse_vmess(url: str) -> Optional[dict]:
    try:
        b64 = url[8:].split('#')[0].split('?')[0]
        b64 += '=' * (4 - len(b64) % 4) if len(b64) % 4 else ''
        decoded = base64.b64decode(b64).decode('utf-8', errors='ignore')
        data = json.loads(decoded)
        address = data.get('add')
        port = data.get('port')
        uuid = data.get('id')
        aid = data.get('aid', '0')
        net = data.get('net', 'tcp')
        security = data.get('security', 'auto')
        sni = data.get('sni', '')
        fp = data.get('fp', 'chrome')
        path = data.get('path', '/')
        host = data.get('host', '')
        tag = data.get('ps', 'vmess')
        return {
            "protocol": "vmess",
            "uuid": uuid,
            "address": address,
            "port": int(port),
            "alterId": int(aid),
            "security": security,
            "type": net,
            "sni": sni,
            "fp": fp,
            "path": path,
            "host": host,
            "tag": tag
        }
    except:
        return None

def parse_ss(url: str) -> Optional[dict]:
    try:
        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc
        if '@' in netloc:
            auth, rest = netloc.split('@', 1)
            if ':' in auth:
                method, password = auth.split(':', 1)
            else:
                method, password = "aes-256-gcm", auth
        else:
            b64 = netloc
            b64 += '=' * (4 - len(b64) % 4) if len(b64) % 4 else ''
            decoded = base64.b64decode(b64).decode('utf-8', errors='ignore')
            if ':' in decoded and '@' not in decoded:
                method, rest = decoded.split(':', 1)
                password, address = rest.split('@', 1)
            else:
                return None
        if ':' in rest:
            address, port_str = rest.split(':', 1)
            port = int(port_str)
        else:
            return None
        return {
            "protocol": "ss",
            "method": method,
            "password": password,
            "address": address,
            "port": port,
            "tag": "ss"
        }
    except:
        return None

def parse_hysteria2(url: str) -> Optional[dict]:
    try:
        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc
        auth = ""
        host = parsed.hostname
        port = parsed.port or 443
        if '@' in netloc:
            auth_part, host_part = netloc.split('@', 1)
            auth = urllib.parse.unquote(auth_part)
            if ':' in host_part:
                host, port_str = host_part.split(':', 1)
                port = int(port_str)
            else:
                host = host_part
        params = urllib.parse.parse_qs(parsed.query)
        def get_q(key, default=""):
            val = params.get(key, [default])
            return urllib.parse.unquote(val[0].strip()) if val[0] else default
        return {
            "protocol": "hysteria2",
            "auth": auth,
            "address": host,
            "port": port,
            "sni": get_q("sni", host),
            "insecure": get_q("insecure", "true").lower() in ("true", "1", "yes"),
            "alpn": get_q("alpn", "h3"),
            "obfs": get_q("obfs", ""),
            "obfs-password": get_q("obfs-password", ""),
            "tag": "hysteria2"
        }
    except:
        return None

def parsed_to_clash_proxy(p: dict) -> Optional[dict]:
    proto = p.get('protocol')
    name = p.get('tag', proto)
    if proto == 'vless':
        proxy = {
            "name": name,
            "type": "vless",
            "server": p['address'],
            "port": p['port'],
            "uuid": p['uuid'],
            "udp": True,
            "tls": p.get('security') in ('tls', 'reality'),
            "servername": p.get('sni', p.get('address', '')),
            "client-fingerprint": p.get('fp', 'chrome'),
            "flow": p.get('flow', 'xtls-rprx-vision'),
        }
        if p.get('security') == 'reality':
            proxy["reality-opts"] = {}
            if p.get('pbk'):
                proxy["reality-opts"]["public-key"] = p['pbk']
            if p.get('sid'):
                proxy["reality-opts"]["short-id"] = p['sid']
        net = p.get('type', 'tcp')
        if net in ('ws', 'websocket'):
            proxy["network"] = "ws"
            if p.get('path') or p.get('host'):
                proxy["ws-opts"] = {}
                if p.get('path'):
                    proxy["ws-opts"]["path"] = p['path']
                if p.get('host'):
                    proxy["ws-opts"]["headers"] = {"Host": p['host']}
        elif net == 'grpc':
            proxy["network"] = "grpc"
            if p.get('serviceName'):
                proxy["grpc-opts"] = {"grpc-service-name": p['serviceName']}
        elif net not in ('tcp',):
            proxy["network"] = net
        return proxy
    elif proto == 'trojan':
        proxy = {
            "name": name,
            "type": "trojan",
            "server": p['address'],
            "port": p['port'],
            "password": p['password'],
            "udp": True,
            "tls": p.get('security') == 'tls',
            "servername": p.get('sni', p.get('address', '')),
        }
        if p.get('fp'):
            proxy["client-fingerprint"] = p['fp']
        net = p.get('type', 'tcp')
        if net in ('ws', 'websocket'):
            proxy["network"] = "ws"
            if p.get('path') or p.get('host'):
                proxy["ws-opts"] = {}
                if p.get('path'):
                    proxy["ws-opts"]["path"] = p['path']
                if p.get('host'):
                    proxy["ws-opts"]["headers"] = {"Host": p['host']}
        elif net == 'grpc':
            proxy["network"] = "grpc"
            if p.get('serviceName'):
                proxy["grpc-opts"] = {"grpc-service-name": p['serviceName']}
        elif net not in ('tcp',):
            proxy["network"] = net
        return proxy
    elif proto == 'vmess':
        proxy = {
            "name": name,
            "type": "vmess",
            "server": p['address'],
            "port": p['port'],
            "uuid": p['uuid'],
            "alterId": p['alterId'],
            "cipher": p['security'],
            "udp": True,
            "tls": bool(p.get('sni')),
            "servername": p.get('sni', ''),
            "client-fingerprint": p.get('fp', 'chrome'),
        }
        net = p.get('type', 'tcp')
        if net == 'ws':
            proxy["network"] = "ws"
            if p.get('path') or p.get('host'):
                proxy["ws-opts"] = {}
                if p.get('path'):
                    proxy["ws-opts"]["path"] = p['path']
                if p.get('host'):
                    proxy["ws-opts"]["headers"] = {"Host": p['host']}
        elif net == 'grpc':
            proxy["network"] = "grpc"
            if p.get('host'):
                proxy["grpc-opts"] = {"grpc-service-name": p['host']}
        elif net not in ('tcp',):
            proxy["network"] = net
        return proxy
    elif proto == 'ss':
        proxy = {
            "name": name,
            "type": "ss",
            "server": p['address'],
            "port": p['port'],
            "cipher": p['method'],
            "password": p['password'],
            "udp": True,
        }
        return proxy
    elif proto == 'hysteria2':
        proxy = {
            "name": name,
            "type": "hysteria2",
            "server": p['address'],
            "port": p['port'],
            "password": p.get('auth', ''),
            "udp": True,
        }
        if p.get('sni'):
            proxy["sni"] = p['sni']
        if p.get('insecure'):
            proxy["skip-cert-verify"] = True
        if p.get('obfs') == 'salamander' and p.get('obfs-password'):
            proxy["obfs"] = "salamander"
            proxy["obfs-password"] = p['obfs-password']
        if p.get('alpn') and p['alpn'] != 'h3':
            proxy["alpn"] = [a.strip() for a in p['alpn'].split(',')]
        return proxy
    return None

def generate_clash_config(proxies: list) -> dict:
    proxy_names = []
    for p in proxies:
        name = p.get("name", "unknown")
        if any(c in name for c in '[]{}#&*!|>\'"%@`,'):
            proxy_names.append(f"'{name}'")
        else:
            proxy_names.append(name)
    return {
        "mixed-port": 7890,
        "allow-lan": False,
        "mode": "rule",
        "log-level": "warning",
        "proxies": proxies,
        "proxy-groups": [
            {
                "name": "ВЫБОР СЕРВЕРА",
                "type": "select",
                "proxies": proxy_names
            }
        ],
        "rules": [
            f"MATCH,{proxy_names[0] if proxy_names else 'DIRECT'}"
        ]
    }

if __name__ == "__main__":
    main()
