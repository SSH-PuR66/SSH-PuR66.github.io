#!/usr/bin/env python3
# cartelkit.py -- three-pillar cartel-infrastructure exploitation kit
# PILLAR 1: OSINT exploitation (IOC harvest, cartel-lexicon scoring, entity graph)
# PILLAR 2: financial chokepoints (real Base58Check/Bech32 validation, ledger
#           flow analytics, common-input clustering)
# PILLAR 3: SDR capture forensics (rtl_power sweep + WAV CTCSS/PTT analysis)
# Zero-dependency stdlib. Pillar 3 runs on REAL captures you feed it; the demo
# tape is synthetic and clearly marked SYNTHETIC. Swap live captures via CLI
# with zero code changes. Authorized defensive research only; not legal advice.
import argparse, csv, hashlib, html as _html, json, math, os, random, re, shutil
import statistics, struct, sys, wave, zipfile, datetime
UTC = lambda: datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

# ============ kitutil: IOC engine + IO ============
_IOC = {
 'onion_v3': r'\b[a-z2-7]{56}\.onion\b',
 'onion_v2': r'(?<![a-z2-7])[a-z2-7]{16}\.onion\b',
 'telegram_url': r'\bt\.me/[A-Za-z0-9_]{5,32}\b',
 'telegram_handle': r'(?<![\w@])@[A-Za-z][A-Za-z0-9_]{4,31}\b',
 'btc_bech32': r'\bbc1[qpzry9x8gf2tvdw0s3jn54khce6mua7l]{11,71}\b',
 'btc_base58': r'\b[13][1-9A-HJ-NP-Za-km-z]{25,34}\b',
 'xmr_address': r'\b4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}\b',
 'session_id': r'\b05[0-9a-fA-F]{64}\b',
 'ipv4': r'\b(?:(?:25[0-5]|2[0-4][0-9]|1?[0-9]{1,2})\.){3}(?:25[0-5]|2[0-4][0-9]|1?[0-9]{1,2})\b',
 'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,63}\b'}
RX = {k: re.compile(v) for k, v in _IOC.items()}
def extract_iocs(text):
    out = {}
    for kind, rx in RX.items():
        seen = []
        for m in rx.finditer(text):
            v = m.group(0)
            if v not in seen: seen.append(v)
        if seen: out[kind] = seen
    if 'email' in out:
        keep = [e for e in out['email'] if not e.lower().endswith('.onion')]
        if keep: out['email'] = keep
        else: del out['email']
    return out
def read_text(path, cap=1000000):
    with open(path, 'rb') as fh: return fh.read(cap + 1)[:cap].decode('utf-8', 'replace')
def sha256_path(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(65536), b''): h.update(chunk)
    return h.hexdigest()
def write_json(path, obj):
    with open(path, 'w', encoding='utf-8') as fh: json.dump(obj, fh, indent=2)

# ============ PILLAR 1: OSINT exploitation ============
LEXICON = {
 'cjng':10,'jalisco nueva generacion':12,'nueva generacion':8,'mencho':10,
 'cuatro letras':9,'matazetas':8,'grupo elite':7,'tropa del infierno':9,
 'nueva plaza':6,'cobro de piso':6,'levanton':5,'plaza':3,'jefe de plaza':6,
 'sicario':4,'halcon':4,'huachicol':5,'cristal':3,'metanfetamina':4,
 'fentanilo':4,'manta':5,'narcobloqueo':5,'narcocorrido':3,'secuestro':4,
 'zapopan':3,'guadalajara':3,'tlajomulco':4,'tonala':3,'tepic':3,
 'colima':3,'michoacan':3,'guanajuato':3,'wickr':6,'threema':4,
 'jabber':5,'xmpp':5,'escrow':5,'droga':4,'mota':3,'perico':4,
 'dron':2,'monstruo':3,'cartel':4,'cobro':2}
def tier(score):
    if score >= 25: return 'PRIORITY-1'
    if score >= 10: return 'INTEREST'
    if score > 0: return 'BACKGROUND'
    return 'NULL'
def score_text(text):
    low = text.lower(); hits = []; total = 0
    for term, w in LEXICON.items():
        n = low.count(term)
        if n: hits.append({'term': term, 'count': n, 'weight': w}); total += w * n
    hits.sort(key=lambda h: -(h['weight'] * h['count']))
    return total, hits
def scan_dir(indir):
    docs = []; index = {}; ttot = {}; syn = False
    exts = ('.txt','.md','.log','.htm','.html','.eml','.json','.csv')
    for fn in sorted(os.listdir(indir)):
        if not fn.lower().endswith(exts): continue
        path = os.path.join(indir, fn)
        if not os.path.isfile(path): continue
        text = read_text(path)
        if 'SYNTHETIC' in text[:4000].upper(): syn = True
        score, hits = score_text(text); iocs = extract_iocs(text)
        for kind, vals in iocs.items():
            for v in vals:
                ent = index.setdefault(v, {'type': kind, 'docs': []})
                if fn not in ent['docs']: ent['docs'].append(fn)
        for h in hits: ttot[h['term']] = ttot.get(h['term'], 0) + h['count']
        docs.append({'file': fn, 'sha256': sha256_path(path), 'chars': len(text),
            'score': score, 'tier': tier(score), 'lex': hits[:8],
            'ioc_counts': {k: len(v) for k, v in iocs.items()}, 'iocs': iocs})
    docs.sort(key=lambda d: -d['score'])
    ents = [{'value': v, 'type': m['type'], 'docs': m['docs']} for v, m in sorted(index.items())]
    links = [e for e in ents if len(e['docs']) >= 2]
    tops = [{'term': t, 'count': c} for t, c in sorted(ttot.items(), key=lambda kv: -kv[1])[:15]]
    return {'dir': indir, 'doc_count': len(docs), 'docs': docs, 'synthetic': syn,
            'entity_count': len(ents), 'entities': ents, 'link_nodes': links, 'top_terms': tops}

# ============ PILLAR 2: financial chokepoints ============
B58 = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
B58I = {c: i for i, c in enumerate(B58)}
B32 = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l'
B32I = {c: i for i, c in enumerate(B32)}
def b58encode(b):
    n = int.from_bytes(b, 'big'); out = ''
    while n > 0:
        n, r = divmod(n, 58); out = B58[r] + out
    pad = 0
    for byte in b:
        if byte == 0: pad += 1
        else: break
    return '1' * pad + out
def b58decode(s):
    n = 0
    for c in s:
        if c not in B58I: return None
        n = n * 58 + B58I[c]
    body = n.to_bytes((n.bit_length() + 7) // 8, 'big') if n else b''
    pad = len(s) - len(s.lstrip('1'))
    return b'\x00' * pad + body
def _sha256d(b): return hashlib.sha256(hashlib.sha256(b).digest()).digest()
def verify_btc_base58(addr):
    raw = b58decode(addr)
    if raw is None or len(raw) < 5: return {'ok': False, 'reason': 'invalid base58'}
    payload = raw[:-4]
    if _sha256d(payload)[:4] != raw[-4:]: return {'ok': False, 'reason': 'checksum mismatch'}
    nets = {0:'mainnet P2PKH',5:'mainnet P2SH',111:'testnet P2PKH',196:'testnet P2SH'}
    net = nets.get(payload[0], 'unknown network 0x%02x' % payload[0])
    return {'ok': len(payload) == 21, 'network': net}
def _hrpexp(hrp): return [ord(c) >> 5 for c in hrp] + [0] + [ord(c) & 31 for c in hrp]
def _polymod(vals):
    gen = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]; chk = 1
    for v in vals:
        top = chk >> 25; chk = ((chk & 33554431) << 5) ^ v
        for i in range(5):
            if (top >> i) & 1: chk ^= gen[i]
    return chk
def _convbits(data, frm, to, pad=True):
    acc = 0; bits = 0; ret = []; maxv = (1 << to) - 1
    for v in data:
        acc = (acc << frm) | v; bits += frm
        while bits >= to:
            bits -= to; ret.append((acc >> bits) & maxv)
    if pad and bits: ret.append((acc << (to - bits)) & maxv)
    return ret
def bech32_encode(hrp, data5):
    pm = _polymod(_hrpexp(hrp) + data5 + [0] * 6) ^ 1
    cs = [(pm >> 5 * (5 - i)) & 31 for i in range(6)]
    return hrp + '1' + ''.join(B32[d] for d in data5 + cs)
def segwit_addr(hrp, witver, witprog):
    return bech32_encode(hrp, [witver] + _convbits(list(witprog), 8, 5))
def verify_bech32(addr):
    if addr != addr.lower() and addr != addr.upper(): return {'ok': False, 'reason': 'mixed case'}
    a = addr.lower()
    if any(ord(c) < 33 or ord(c) > 126 for c in a): return {'ok': False, 'reason': 'bad char range'}
    pos = a.rfind('1')
    if pos < 1 or pos + 7 > len(a): return {'ok': False, 'reason': 'missing hrp/separator'}
    hrp, data = a[:pos], a[pos + 1:]
    if not data or any(c not in B32I for c in data): return {'ok': False, 'reason': 'bad charset'}
    pm = _polymod(_hrpexp(hrp) + [B32I[c] for c in data])
    if pm == 1: return {'ok': True, 'network': 'segwit v0 (bech32)'}
    if pm == 0x2bc830a3: return {'ok': True, 'network': 'segwit v1+ (bech32m)'}
    return {'ok': False, 'reason': 'checksum mismatch'}
def validate_wallet(value):
    v = value.strip()
    if v[:3].lower() == 'bc1': return _vr(v, 'BTC', verify_bech32(v))
    if v[:1] in ('1', '3'): return _vr(v, 'BTC', verify_btc_base58(v))
    if v[:1] == '4' and len(v) == 95:
        return {'value': v, 'asset': 'XMR', 'ok': None, 'status': 'format-only (Keccak-256 outside stdlib; checksum not verified)'}
    return {'value': v, 'asset': 'UNKNOWN', 'ok': None, 'status': 'unrecognized scheme'}
def _vr(v, asset, r):
    if r.get('ok'): return {'value': v, 'asset': asset, 'ok': True, 'status': 'checksum-OK - ' + r.get('network', '')}
    return {'value': v, 'asset': asset, 'ok': False, 'status': 'checksum-FAIL - ' + r.get('reason', '')}
def analyze_ledger(path):
    rows = []
    with open(path, newline='', encoding='utf-8-sig') as fh:
        for row in csv.DictReader(fh):
            try: amt = float((row.get('amount') or '0').strip() or 0)
            except ValueError: continue
            rows.append({'ts': (row.get('ts') or '').strip(), 'src': (row.get('src') or '').strip(),
                         'dst': (row.get('dst') or '').strip(), 'amount': amt,
                         'asset': (row.get('asset') or 'XBT').strip()})
    wal = {}
    def W(a): return wal.setdefault(a, {'in_amt':0.0,'out_amt':0.0,'in_n':0,'out_n':0,'outs':[]})
    for r in rows:
        s = W(r['src']); d = W(r['dst'])
        s['out_amt'] += r['amount']; s['out_n'] += 1
        s['outs'].append({'ts': r['ts'], 'amount': r['amount'], 'dst': r['dst']})
        d['in_amt'] += r['amount']; d['in_n'] += 1
    flags = []
    for w, s in wal.items():
        band = [o for o in s['outs'] if 850 <= o['amount'] < 1000]
        if len(band) >= 4:
            flags.append({'kind':'STRUCTURING','wallet':w,'detail':'%d outputs in 850-999 band - report-threshold probing' % len(band)})
        if s['out_n'] >= 8:
            flags.append({'kind':'DISPERSION-HUB','wallet':w,'detail':'%d outputs totalling %.2f - fan-out laundering profile' % (s['out_n'], s['out_amt'])})
    done = set()
    for w, s in wal.items():
        if w in done or not s['outs']: continue
        chain = [w]; cur = w; hops = 0
        while hops < 10:
            cand = []
            for o in wal.get(cur, {}).get('outs', []):
                ref = wal.get(o['dst'])
                if ref is None: continue
                for o2 in ref['outs']:
                    if 0.85 * o['amount'] <= o2['amount'] <= 0.999 * o['amount']: cand.append(o['dst'])
            cand = sorted(set(cand))
            if len(cand) != 1 or cand[0] in chain: break
            chain.append(cand[0]); cur = cand[0]; hops += 1
        if len(chain) >= 4:
            done.update(chain)
            flags.append({'kind':'PEEL-CHAIN','wallet':' -> '.join(chain),'detail':'relay of slightly-decreasing transfers - chain-hopping profile'})
    tin = sorted(wal.items(), key=lambda kv: -kv[1]['in_amt'])[:10]
    tout = sorted(wal.items(), key=lambda kv: -kv[1]['out_amt'])[:10]
    return {'sha256': sha256_path(path), 'txs': len(rows), 'wallets': len(wal),
            'top_receivers': [{'wallet': w, 'amt': round(s['in_amt'],2), 'n': s['in_n']} for w, s in tin if s['in_amt'] > 0],
            'top_senders': [{'wallet': w, 'amt': round(s['out_amt'],2), 'n': s['out_n']} for w, s in tout if s['out_amt'] > 0],
            'flags': flags}
def cluster_common_inputs(path):
    parent = {}
    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb: parent[ra] = rb
    txs = 0
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if not line: continue
            try: o = json.loads(line)
            except ValueError: continue
            txs += 1
            vins = [str(v) for v in (o.get('vin') or [])]
            for i in range(1, len(vins)):
                if vins[0] != vins[i]: union(vins[0], vins[i])
    groups = {}
    for x in parent: groups.setdefault(find(x), set()).add(x)
    cls = sorted((sorted(g) for g in groups.values() if len(g) >= 2), key=lambda c: -len(c))
    return {'sha256': sha256_path(path), 'tx_parsed': txs, 'cluster_count': len(cls),
            'wallets_clustered': sum(len(c) for c in cls), 'clusters': cls}

# ============ PILLAR 3: SDR capture forensics ============
CTCSS = [67.0,69.3,71.9,74.4,77.0,79.7,82.5,85.4,88.5,91.5,94.8,97.4,100.0,103.5,
 107.2,110.9,114.8,118.8,123.0,127.3,131.8,136.5,141.3,146.2,151.4,156.7,159.8,
 162.2,165.5,167.9,171.3,173.8,177.3,179.9,183.5,186.2,189.9,192.8,196.6,199.5,
 203.5,206.5,210.7,218.1,225.7,229.1,233.6,241.8,250.3,254.1]
def _goertzel(x, fs, f):
    w = 2.0 * math.pi * f / fs; cw = 2.0 * math.cos(w); s1 = s2 = 0.0
    for v in x: s0 = v + cw * s1 - s2; s2 = s1; s1 = s0
    return math.sqrt(max(s1*s1 + s2*s2 - cw*s1*s2, 0.0)) / max(len(x), 1)
def analyze_rtl_power(path):
    sweeps = []
    with open(path, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith('#'): continue
            parts = [p.strip() for p in line.split(',')]
            if len(parts) < 8: continue
            try:
                lo = float(parts[2]); step = float(parts[4]); n = int(float(parts[5]))
                vals = [float(x) for x in parts[6:6 + n]]
            except ValueError: continue
            if vals: sweeps.append((lo, step, vals, parts[0] + 'T' + parts[1] + 'Z'))
    if not sweeps: return {'error': 'no rtl_power sweeps parsed'}
    lo, step, _, _ts0 = sweeps[0]
    n = max(len(v) for _, _, v, _ts in sweeps)
    acc = [[] for _ in range(n)]
    for _, _, vals, _ts in sweeps:
        for i, v in enumerate(vals): acc[i].append(v)
    allv = [v for series in acc for v in series]
    floor = statistics.median(allv); thr = floor + 9.0
    carriers = []
    for i in range(n):
        series = acc[i]
        if not series: continue
        peak = max(series); occ = sum(1 for v in series if v > thr) / len(series)
        if peak > thr and occ >= 0.05:
            mhz = (lo + step * i) / 1e6
            if occ >= 0.9: klass = 'continuous (broadcast/repeater/telemetry)'
            elif occ >= 0.15: klass = 'intermittent (PTT-pattern traffic)'
            else: klass = 'sporadic burst'
            carriers.append({'mhz': round(mhz,5), 'peak_db': round(peak,1),
                             'delta_db': round(peak-floor,1), 'occupancy': round(occ,3), 'class': klass})
    carriers.sort(key=lambda c: -c['peak_db'])
    pmax = [max(a) if a else floor for a in acc]
    kk = max(1, len(pmax) // 160)
    spec = [round(max(pmax[i:i+kk]), 1) for i in range(0, len(pmax), kk)][:160]
    ptt_bin = None; ptt_mhz = None
    for c in carriers:
        if 'PTT' in c['class']:
            ptt_bin = int(round((c['mhz'] * 1e6 - lo) / step)); ptt_mhz = c['mhz']; break
    ptt_track = []
    if ptt_bin is not None and 0 <= ptt_bin < n:
        for k, (_l, _s, _v, _t) in enumerate(sweeps):
            act = (k < len(acc[ptt_bin])) and (acc[ptt_bin][k] > thr)
            ptt_track.append({'ts': _t, 'active': act})
    return {'sweeps': len(sweeps), 'bins': n, 'noise_floor_db': round(floor,1),
            'threshold_db': round(thr,1), 'carrier_count': len(carriers),
            'band_mhz': [round(lo/1e6,3), round((lo + step*(n-1))/1e6,3)], 'carriers': carriers[:25],
            'spectrum_max_db': spec, 'ptt_track': ptt_track, 'ptt_mhz': ptt_mhz}
def _decode_wav(path):
    w = wave.open(path, 'rb')
    ch = w.getnchannels(); sw = w.getsampwidth(); fs = w.getframerate()
    n = min(w.getnframes(), fs * 6); raw = w.readframes(n); w.close()
    if sw == 2:
        cnt = len(raw) // 2; vals = struct.unpack('<%dh' % cnt, raw[:cnt*2])
        x = [vals[i] / 32768.0 for i in range(0, cnt, ch)]
    elif sw == 1: x = [(b - 128) / 128.0 for b in raw[0::ch]]
    else: raise ValueError('unsupported sample width: %d' % sw)
    return x, fs
def analyze_wav(path):
    x, fs = _decode_wav(path)
    abs0 = None
    _mp = (path[:path.rfind('.')] + '_META.json') if '.' in path else (path + '_META.json')
    if os.path.isfile(_mp):
        try: abs0 = json.load(open(_mp, encoding='utf-8')).get('start_utc')
        except Exception: abs0 = None
    win = max(1, fs // 20); env = []
    for i in range(0, len(x) - win, win):
        seg = x[i:i + win]; env.append(math.sqrt(sum(v*v for v in seg) / win))
    floor = statistics.median(env) if env else 0.0
    thr = max(floor * 4.0, 1e-4)
    bursts = []; cur = None; gap = 3
    for i, e in enumerate(env):
        if e > thr:
            if cur is None: cur = [i, i]
            else: cur[1] = i
        elif cur is not None and i - cur[1] > gap:
            bursts.append((cur[0], cur[1])); cur = None
    if cur is not None: bursts.append((cur[0], cur[1]))
    durs = [(b - a + 1) * win / fs for (a, b) in bursts]
    duty = sum(1 for e in env if e > thr) / max(len(env), 1)
    factor = max(1, int(fs // 2000))
    seg = x[:min(len(x), factor * 2000)]
    ds = []
    for i in range(0, len(seg) - factor, factor): ds.append(sum(seg[i:i + factor]) / factor)
    eff = fs / factor; mags = []
    for f in CTCSS:
        if f < eff / 2 and ds: mags.append((f, _goertzel(ds, eff, f)))
    med = statistics.median([m for _, m in mags]) if mags else 0.0
    tones = [{'hz': f, 'snr': round(m / max(med, 1e-9), 1)} for f, m in mags if m > med * 6 and m > 1e-6]
    tones.sort(key=lambda t: -t['snr'])
    lock = None
    if tones:
        top = tones[0]
        mg = round(top['snr'] / tones[1]['snr'], 1) if len(tones) > 1 else None
        if len(tones) == 1 or top['snr'] >= 3.0 * tones[1]['snr']:
            lock = {'hz': top['hz'], 'snr': top['snr'], 'margin': mg}
    abs_b = []
    if abs0:
        try:
            _t0 = datetime.datetime.strptime(abs0, '%Y-%m-%dT%H:%M:%SZ')
            abs_b = [(_t0 + datetime.timedelta(seconds=(a2 * win) / fs)).strftime('%Y-%m-%dT%H:%M:%SZ') for (a2, _b2) in bursts]
        except Exception: abs_b = []
    return {'sample_rate': fs, 'seconds': round(len(x)/fs,2), 'burst_count': len(bursts),
            'burst_durations_s': [round(d,2) for d in durs][:12], 'duty_cycle': round(duty,3),
            'ctcss_detected': tones[:6], 'ctcss_lock': lock, 'abs_bursts_utc': abs_b,
            'note': 'CTCSS subtone present = closed-access radio usage (community/repeater); absent = open squelch'}

def _parse_day(s):
    s = (s or '').strip()
    for cand, fmt in ((s[:19], '%Y-%m-%dT%H:%M:%S'), (s[:10], '%Y-%m-%d')):
        try: return datetime.datetime.strptime(cand, fmt)
        except Exception: pass
    return None
def tempo_fusion(ledger_path, sweep_res, wav_res):
    money = []
    try:
        with open(ledger_path, newline='', encoding='utf-8-sig') as fh:
            for row in csv.DictReader(fh):
                ts = (row.get('ts') or '').strip()
                if ts.startswith('#'): continue
                d = _parse_day(ts)
                if d: money.append({'ts': ts, 'day': d.strftime('%Y-%m-%d'),
                    'label': '%s -> %s (%s %s)' % ((row.get('src') or '').strip(), (row.get('dst') or '').strip(), (row.get('amount') or '').strip(), (row.get('asset') or '').strip())})
    except Exception: pass
    rf_days = {}
    for t in ((sweep_res or {}).get('ptt_track') or []):
        d = _parse_day(t.get('ts', ''))
        if not d: continue
        key = d.strftime('%Y-%m-%d')
        agg = rf_days.setdefault(key, {'active': 0, 'total': 0})
        agg['total'] += 1
        if t.get('active'): agg['active'] += 1
    wav_b = (wav_res or {}).get('abs_bursts_utc') or []
    wav_days = []
    for x in wav_b:
        d = _parse_day(x)
        if d: wav_days.append(d.strftime('%Y-%m-%d'))
    coin = []
    for m in money:
        rf = rf_days.get(m['day']); ra = rf['active'] if rf else 0
        wb = wav_days.count(m['day'])
        if ra or wb: coin.append({'money': m['label'], 'day': m['day'], 'rf_active_sweeps': ra, 'wav_bursts': wb})
    flags = []
    if sum(1 for c in coin if c['rf_active_sweeps'] > 0) >= 2:
        flags.append({'kind': 'TEMPO-CORR', 'detail': 'money movement days coincide with PTT-pattern RF activity near %.3f MHz - operational tempo correlation' % ((sweep_res or {}).get('ptt_mhz') or 0.0)})
    if any(c['wav_bursts'] for c in coin):
        flags.append({'kind': 'COMMS-PAYMENT-COINCIDENCE', 'detail': 'recorded keyed bursts land on a ledger payment day'})
    return {'money_events': len(money), 'rf_days': rf_days, 'wav_bursts_abs': wav_b,
            'coincidences': coin, 'flags': flags,
            'note': 'day-granularity correlation (ledger timestamps are date-only); coincidence is a lead, not proof'}
def svg_timeline(tp):
    days = sorted(set(list((tp.get('rf_days') or {}).keys()) + [c['day'] for c in (tp.get('coincidences') or [])]))
    if not days: return ''
    d0 = _parse_day(days[0]); d1 = _parse_day(days[-1])
    if not d0 or not d1: return ''
    span = max((d1 - d0).days, 1)
    W, H = 860, 120
    def X(day):
        d = _parse_day(day)
        return 8.0 + (d - d0).days * (W - 60) / span if d else 8.0
    out = ['<svg width="%d" height="%d" style="background:#0d1412;border:1px solid #1d3a35;margin:8px 0">' % (W, H)]
    out.append('<line x1="0" y1="45" x2="%d" y2="45" stroke="#1d3a35"/>' % W)
    out.append('<line x1="0" y1="95" x2="%d" y2="95" stroke="#1d3a35"/>' % W)
    out.append('<text x="4" y="14" fill="#37e0c8" font-size="11">RF LANE (PTT-pattern activity)</text>')
    out.append('<text x="4" y="66" fill="#ffb454" font-size="11">MONEY LANE (ledger events)</text>')
    for day, agg in sorted((tp.get('rf_days') or {}).items()):
        x = X(day)
        h = min(30.0, 4.0 + 15.0 * agg['active'] / max(agg['total'], 1))
        out.append('<rect x="%.1f" y="%.1f" width="7" height="%.1f" fill="%s"/>' % (x, 45 - h, h, '#37e0c8' if agg['active'] else '#1d3a35'))
    for c in (tp.get('coincidences') or []):
        x = X(c['day'])
        out.append('<rect x="%.1f" y="97" width="7" height="11" fill="#ffb454"/>' % x)
        out.append('<line x1="%.1f" y1="6" x2="%.1f" y2="112" stroke="#ff6b5e" stroke-dasharray="3 3"/>' % (x + 3.5, x + 3.5))
    out.append('<text x="8" y="%d" fill="#4d7a72" font-size="11">%s</text>' % (H - 2, days[0]))
    out.append('<text x="%d" y="%d" fill="#4d7a72" font-size="11" text-anchor="end">%s</text>' % (W - 8, H - 2, days[-1]))
    out.append('</svg>')
    return ''.join(out)


# ============ synthetic demo tape forge ============
def forge(tape):
    di = os.path.join(tape, 'intel'); os.makedirs(di, exist_ok=True)
    random.seed(1337)
    onion = ''.join(random.choice('abcdefghijklmnopqrstuvwxyz234567') for _ in range(56)) + '.onion'
    b32ok = segwit_addr('bc', 0, bytes(range(1, 21)))
    bad = list(b32ok); bad[20] = 'p' if bad[20] != 'p' else 'q'; b32bad = ''.join(bad)
    payload = b'\x00' + bytes(range(21, 41)); b58ok = b58encode(payload + _sha256d(payload)[:4])
    xmr = '4' + random.choice('0123456789AB') + ''.join(random.choice(B58) for _ in range(93))
    sess = '05' + ''.join(random.choice('0123456789abcdef') for _ in range(64))
    hdr = 'SYNTHETIC DEMO TAPE - TRAINING DATA, NOT REAL INTEL.\n\n'
    open(os.path.join(di, 'leak_A.txt'), 'w', encoding='utf-8').write(hdr +
      'Intercepted TG chat log (translated). CJNG jefe de plaza in Tlajomulco moving cristal; '
      'cobro de piso collections weekly via halcon runners. Mencho loyalists, Grupo Elite security. '
      'Paymaster handle @plazabossgdl (t.me/plazabossgdl) - escrow deals on ' + onion + ' '
      'session id ' + sess + ' . Remit wickr only. BTC settlement addr ' + b32ok + '\n'
      'Sicario crew rotation Zapopan / Guadalajara. Dron overwatch noted near plaza routes.\n')
    open(os.path.join(di, 'leak_B.txt'), 'w', encoding='utf-8').write(hdr +
      'Forum dump scrape: vendor claims Matazetas ties, fentanilo precursors through Manzanillo. '
      'Contact repeats: @plazabossgdl and same market ' + onion + ' . Monstruo (improvised APC) '
      'spotted Michoacan. Old payout address ' + b58ok + ' . XMR fallback ' + xmr + ' . '
      'Possible fat-fingered addr posted then deleted: ' + b32bad + ' . Narcobloqueo threats Guanajuato.\n')
    open(os.path.join(di, 'leak_C.txt'), 'w', encoding='utf-8').write(hdr +
      'Background noise: local news chatter about a dron sighting and plaza vendors paying cobro. '
      'No identifiers. Mostly irrelevant.\n')
    led = os.path.join(tape, 'ledger.csv')
    with open(led, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh); w.writerow(['ts','src','dst','amount','asset'])
        w.writerow(['# SYNTHETIC DEMO TAPE','','','',''])
        for i in range(6): w.writerow(['2024-01-0%d' % (i+1), 'STREET-%d' % i, 'BOSS', 2500, 'XBT'])
        w.writerow(['2024-01-10','BOSS','HUB1',9000,'XBT'])
        for i, a in enumerate([880, 905, 930, 999]): w.writerow(['2024-01-11','HUB1','S%d' % i, a, 'XBT'])
        for i, a in enumerate([450, 500, 520, 600, 640, 700]): w.writerow(['2024-01-12','HUB1','D%d' % i, a, 'XBT'])
        w.writerow(['2024-02-01','PREPAID','PA',1000,'XBT']); w.writerow(['2024-02-02','PA','PB',950,'XBT'])
        w.writerow(['2024-02-03','PB','PC',900,'XBT']); w.writerow(['2024-02-04','PC','PD',870,'XBT'])
        w.writerow(['2024-02-05','PD','PE',860,'XBT'])
    cl = os.path.join(tape, 'clusters.jsonl')
    with open(cl, 'w', encoding='utf-8') as fh:
        fh.write(json.dumps({'tx':'t1','vin':['W-A','W-B','W-C']}) + '\n')
        fh.write(json.dumps({'tx':'t2','vin':['W-C','W-D']}) + '\n')
        fh.write(json.dumps({'tx':'t3','vin':['W-X']}) + '\n')
    sw = os.path.join(tape, 'sweep.csv')
    lo = 446000000.0; step = 2000.0; nb = 500
    with open(sw, 'w', encoding='utf-8') as fh:
        fh.write('# SYNTHETIC rtl_power-format demo sweep\n')
        for i in range(30):
            vals = [-42.0 + random.gauss(0, 0.6) for _ in range(nb)]
            vals[120] += 26.0
            if i % 5 in (0, 1): vals[310] += 18.0
            if i in (7, 19): vals[400] += 14.0
            _ts = datetime.datetime(2024, 1, 20, 6, 0, 0) + datetime.timedelta(days=i % 5, hours=i // 5)
            row = [_ts.strftime('%Y-%m-%d'), _ts.strftime('%H:%M:%S'),
                   '%.0f' % lo, '%.0f' % (lo + step * nb), '%.1f' % step, str(nb)] + ['%.1f' % v for v in vals]
            fh.write(', '.join(row) + '\n')
    wv = os.path.join(tape, 'capture_SYNTHETIC.wav')
    fs = 8000; secs = 6; bkey = [(0.5,1.4),(2.2,2.9),(4.0,4.8)]
    frames = []
    for nn in range(fs * secs):
        t = nn / fs
        keyed = any(a <= t <= b for a, b in bkey)
        v = 0.02 * random.uniform(-1, 1)
        if keyed:
            v += 0.15 * math.sin(2*math.pi*88.5*t) + 0.6 * math.sin(2*math.pi*800*t) + 0.2 * random.uniform(-1, 1)
        v = max(-1.0, min(1.0, v)); frames.append(int(v * 32767))
    w = wave.open(wv, 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(fs)
    w.writeframes(struct.pack('<%dh' % len(frames), *frames)); w.close()
    open(wv[:wv.rfind('.')] + '_META.json', 'w', encoding='utf-8').write(json.dumps({'start_utc': '2024-02-01T09:00:00Z'}))
    open(os.path.join(tape, 'README_SYNTHETIC.txt'), 'w', encoding='utf-8').write(
        'SYNTHETIC DEMO TAPE. Every artifact in this folder is forged training data '
        'for pipeline verification. Real addresses are generated with VALID checksums '
        'by the kit itself (plus one deliberately corrupted). Not real intel.\n')
    return {'intel': di, 'ledger': led, 'clusters': cl, 'sweep': sw, 'wav': wv}

# ============ dossier renderer (TLP bar / TAC-TERM chrome) ============
CSS = ('body{background:#0a0f0e;color:#8fd6cb;font-family:Consolas,Menlo,monospace;margin:0;padding:0 24px 60px}'
 '.tlp{background:#ffc000;color:#000;text-align:center;font-weight:bold;letter-spacing:2px;padding:6px;margin:0 -24px 18px}'
 'h1{color:#37e0c8;border-bottom:2px solid #1d3a35;padding-bottom:8px;letter-spacing:1px}'
 'h2{color:#ffb454;margin-top:34px;border-left:4px solid #ffb454;padding-left:10px}'
 'table{border-collapse:collapse;width:100%;font-size:13px;margin:10px 0}'
 'th{background:#122019;color:#37e0c8;border:1px solid #1d3a35;padding:6px;text-align:left}'
 'td{border:1px solid #1d3a35;padding:5px;vertical-align:top;word-break:break-all}'
 '.ok{color:#5be37a}.bad{color:#ff6b5e}.p1{background:#3a2a10;color:#ffc000;font-weight:bold;padding:2px 6px}'
 '.chip{background:#122019;border:1px solid #1d3a35;padding:2px 7px;margin:2px;display:inline-block;border-radius:3px}'
 '.syn{background:#2a1503;color:#ffb454;border:1px dashed #ffb454;padding:10px;margin:14px 0;font-size:13px}'
 '.meta{color:#4d7a72;font-size:12px}.flag{color:#ffb454} code{color:#37e0c8}')

def svg_spectrum(s):
    spec = s.get('spectrum_max_db') or []
    if not spec:
        return ''
    W, H = 860, 130
    lo, hi = s['band_mhz'][0], s['band_mhz'][1]
    fmin = min(spec); fmax = max(spec); rng = max(fmax - fmin, 0.001)
    n = len(spec)
    pts = []
    for i, v in enumerate(spec):
        x = i * W / max(n - 1, 1)
        y = H - (v - fmin) / rng * (H - 18) - 6
        pts.append('%.1f,%.1f' % (x, y))
    ty = H - (s['threshold_db'] - fmin) / rng * (H - 18) - 6
    ty = max(2.0, min(H - 2.0, ty))
    out = ['<svg width="%d" height="%d" style="background:#0d1412;border:1px solid #1d3a35;margin:8px 0">' % (W, H)]
    out.append('<line x1="0" y1="%.1f" x2="%d" y2="%.1f" stroke="#ff6b5e" stroke-dasharray="4 4"/>' % (ty, W, ty))
    for c in s['carriers']:
        fx = (c['mhz'] - lo) / max(hi - lo, 0.0001) * W
        out.append('<line x1="%.1f" y1="2" x2="%.1f" y2="%d" stroke="#ffb454" stroke-dasharray="3 3"/>' % (fx, fx, H - 2))
    out.append('<polyline points="%s" fill="none" stroke="#37e0c8" stroke-width="1"/>' % ' '.join(pts))
    out.append('<text x="4" y="14" fill="#4d7a72" font-size="11">%.3f MHz</text>' % lo)
    out.append('<text x="%d" y="14" fill="#4d7a72" font-size="11" text-anchor="end">%.3f MHz</text>' % (W - 4, hi))
    out.append('</svg>')
    return ''.join(out)

def esc(x): return _html.escape(str(x))
def tbl(headers, rows):
    s = '<table><tr>' + ''.join('<th>%s</th>' % esc(h) for h in headers) + '</tr>'
    for r in rows: s += '<tr>' + ''.join('<td>%s</td>' % c for c in r) + '</tr>'
    return s + '</table>'
def render(res, out_html, synthetic):
    S = ['<html><head><meta charset="utf-8"><title>CARTELKIT // TAC-TERM DOSSIER</title><style>%s</style></head><body>' % CSS]
    S.append('<div class="tlp">TLP:AMBER // TAC-TERM // CARTELKIT DOSSIER</div>')
    S.append('<h1>CARTELKIT v1.0 -- FUSED INTELLIGENCE DOSSIER</h1>')
    S.append('<div class="meta">Generated %s UTC | Passive-collection discipline: no live-target claims beyond supplied captures.</div>' % UTC())
    if synthetic: S.append('<div class="syn"><b>SYNTHETIC DEMO DATASET</b> -- every indicator below was forged in-lab for pipeline verification. Swap live captures/dumps via CLI; zero code changes required.</div>')
    if 'osint' in res:
        o = res['osint']
        S.append('<h2>PILLAR 1 -- OSINT EXPLOITATION</h2>')
        S.append('<div>%d docs scanned | %d unique entities | %d cross-doc link nodes</div>' % (o['doc_count'], o['entity_count'], len(o['link_nodes'])))
        rows = []
        for d in o['docs']:
            tcls = '<span class="p1">%s</span>' % d['tier'] if d['tier'] == 'PRIORITY-1' else esc(d['tier'])
            lex = ', '.join('%s x%d' % (h['term'], h['count']) for h in d['lex'])
            rows.append([esc(d['file']), tcls, str(d['score']), esc(json.dumps(d['ioc_counts'])), esc(lex)])
        S.append(tbl(['file','tier','score','iocs','top lexical hits'], rows))
        if o['link_nodes']:
            S.append('<h3>LINK NODES (entity appears in 2+ docs)</h3>')
            S.append(tbl(['entity','type','docs'], [[esc(e['value']), esc(e['type']), esc(', '.join(e['docs']))] for e in o['link_nodes']]))
        S.append('<h3>ENTITIES</h3>')
        S.append(''.join('<span class="chip">%s <i>(%s)</i></span>' % (esc(e['value']), esc(e['type'])) for e in o['entities'][:60]))
    if 'validate' in res:
        S.append('<h2>PILLAR 2a -- WALLET CHECKSUM VALIDATION (BIP-173 / Base58Check)</h2>')
        rows = []
        for v in res['validate']:
            st = '<span class="ok">%s</span>' % esc(v['status']) if v['ok'] else ('<span class="bad">%s</span>' % esc(v['status']) if v['ok'] is False else esc(v['status']))
            rows.append([esc(v['value']), esc(v['asset']), st])
        S.append(tbl(['address','asset','verdict'], rows))
    if 'fin_ledger' in res:
        f = res['fin_ledger']
        S.append('<h2>PILLAR 2b -- LEDGER FLOW ANALYTICS</h2>')
        S.append('<div>%d txs | %d wallets | sha256: %s</div>' % (f['txs'], f['wallets'], esc(f['sha256'][:16] + '...')))
        if f['flags']:
            S.append('<h3>BEHAVIORAL FLAGS</h3>')
            S.append(tbl(['pattern','wallet(s)','detail'], [['<span class="flag">%s</span>' % esc(x['kind']), esc(x['wallet']), esc(x['detail'])] for x in f['flags']]))
        S.append(tbl(['top receivers','amt','in-n'], [[esc(r['wallet']), r['amt'], r['n']] for r in f['top_receivers'][:6]]))
        S.append(tbl(['top senders','amt','out-n'], [[esc(s['wallet']), s['amt'], s['n']] for s in f['top_senders'][:6]]))
    if 'fin_clusters' in res:
        c = res['fin_clusters']
        S.append('<h2>PILLAR 2c -- COMMON-INPUT CLUSTERING</h2>')
        S.append('<div>%d txs parsed | %d clusters | %d wallets clustered</div>' % (c['tx_parsed'], c['cluster_count'], c['wallets_clustered']))
        for i, cl in enumerate(c['clusters']): S.append('<div class="chip">cluster-%d: %s</div>' % (i, esc(', '.join(cl))))
    if 'sdr_sweep' in res:
        s = res['sdr_sweep']
        S.append('<h2>PILLAR 3a -- RF SWEEP ANALYSIS (rtl_power)</h2>')
        S.append('<div>%d sweeps | band %.3f-%.3f MHz | noise floor %.1f dB | %d carriers above +9dB occupancy rule</div>'
                 % (s['sweeps'], s['band_mhz'][0], s['band_mhz'][1], s['noise_floor_db'], s['carrier_count']))
        S.append(svg_spectrum(s))
        S.append(tbl(['MHz','peak dB','delta dB','occupancy','classification'],
          [[c['mhz'], c['peak_db'], c['delta_db'], c['occupancy'], esc(c['class'])] for c in s['carriers']]))
    if 'sdr_wav' in res:
        w = res['sdr_wav']
        S.append('<h2>PILLAR 3b -- WAV COMMS FORENSICS</h2>')
        S.append('<div>%s Hz | %ss | %d PTT bursts | durations %s | duty cycle %.3f</div>'
                 % (w['sample_rate'], w['seconds'], w['burst_count'], esc(w['burst_durations_s']), w['duty_cycle']))
        lk = w.get('ctcss_lock')
        if lk:
            mg = ('%.1fx dominance margin over nearest neighbor' % lk['margin']) if lk.get('margin') else 'sole tone above floor'
            S.append('<div>CTCSS LOCK: <span class="ok"><b>%.1f Hz</b></span> | SNR %.1f | %s</div>' % (lk['hz'], lk['snr'], mg))
        if w['ctcss_detected']:
            S.append(tbl(['CTCSS tone (Hz)','SNR vs floor'], [[t['hz'], t['snr']] for t in w['ctcss_detected']]))
        S.append('<div class="meta">%s</div>' % esc(w['note']))
    if 'tempo' in res:
        tp = res['tempo']
        S.append('<h2>PILLAR 4 -- CROSS-SENSOR TEMPO FUSION</h2>')
        S.append('<div>%d ledger events coincide with RF / recorded-comms activity</div>' % len(tp['coincidences']))
        S.append(svg_timeline(tp))
        if tp['flags']:
            S.append(tbl(['flag','detail'], [['<span class="flag">%s</span>' % esc(f['kind']), esc(f['detail'])] for f in tp['flags']]))
        if tp['coincidences']:
            S.append(tbl(['money event','day','rf-active sweeps','wav bursts'], [[esc(c['money']), esc(c['day']), c['rf_active_sweeps'], c['wav_bursts']] for c in tp['coincidences'][:20]]))
        S.append('<div class="meta">%s</div>' % esc(tp['note']))
    S.append('<h2>METHOD / PROVENANCE</h2><div class="meta">All artifacts SHA-256 listed in MANIFEST.sha256. Wallet validation implements BIP-173 polymod + Base58Check in-pure-Python (independently recomputable). RF analysis accepts real rtl_power / rtl_power_fftw CSV and WAV captures via CLI. Authorized defensive research only -- not legal advice.</div>')
    S.append('</body></html>')
    open(out_html, 'w', encoding='utf-8').write(''.join(S))

README_TXT = '''CARTELKIT v1.0 -- three-pillar cartel-infrastructure exploitation kit
Zero-dependency (Python 3.8+ stdlib only). Passive-collection discipline.

DEMO (end-to-end, synthetic tape):
  python cartelkit.py all --out cartelkit_out

LIVE SWAP-IN (zero code changes -- CLI only):
  python cartelkit.py osint        --dir  intercepted_dumps/        --out out/osint.json
  python cartelkit.py fin-validate --addr bc1q... 
  python cartelkit.py fin-ledger   --csv  ledger.csv                --out out/ledger.json
  python cartelkit.py fin-clusters --jsonl vin_stream.jsonl         --out out/clusters.json
  python cartelkit.py sdr-sweep    --csv  rtl_power_fftw_capture.csv --out out/sweep.json
  python cartelkit.py sdr-wav      --wav  capture.wav               --out out/wav.json
  python cartelkit.py run --intel dumps/ --ledger ledger.csv --sweep cap.csv --wav cap.wav --out out
    (any subset of flags; fuses whatever is supplied + dossier.html + zip)

PILLARS:
 1 OSINT exploitation  -- onion v2/v3, TG handles/URLs, Session IDs, Jabber/Wickr,
    BTC/XMR wallets, IPv4, email harvesting; weighted cartel-lexicon scoring
    (PRIORITY-1 / INTEREST / BACKGROUND tiers); entity co-occurrence link nodes.
 2 Financial chokepoints -- genuine Base58Check + Bech32/Bech32m checksum proof
    (BIP-173 polymod), ledger flow analytics (structuring, dispersion hubs,
    peel chains), union-find common-input address clustering.
 3 SDR capture forensics -- rtl_power sweep carrier discovery + occupancy
    classification (repeater vs PTT-pattern vs sporadic), WAV PTT-burst timing
    + CTCSS subtone detection (Goertzel bank over all 50 standard tones).

Authorized defensive research only. Not legal advice.
'''

# ============ fusion pipeline ============
def run_pipeline(out, intel=None, ledger=None, clusters=None, sweep=None, wav=None):
    resd = os.path.join(out, 'results'); os.makedirs(resd, exist_ok=True)
    res = {}; synthetic = False
    if intel:
        print('[1/5] PILLAR 1: OSINT exploitation ->', intel)
        res['osint'] = scan_dir(intel); synthetic = synthetic or res['osint']['synthetic']
        write_json(os.path.join(resd, 'osint.json'), res['osint'])
        vals = []
        for e in res['osint']['entities']:
            if e['type'] in ('btc_bech32', 'btc_base58', 'xmr_address'): vals.append(e['value'])
        if vals:
            print('      validating %d wallet candidates' % len(vals))
            res['validate'] = [validate_wallet(v) for v in vals]
            write_json(os.path.join(resd, 'fin_validate.json'), res['validate'])
    if ledger:
        print('[2/5] PILLAR 2: ledger flow analytics ->', ledger)
        res['fin_ledger'] = analyze_ledger(ledger)
        write_json(os.path.join(resd, 'fin_ledger.json'), res['fin_ledger'])
    if clusters:
        print('[3/5] PILLAR 2: common-input clustering ->', clusters)
        res['fin_clusters'] = cluster_common_inputs(clusters)
        write_json(os.path.join(resd, 'fin_clusters.json'), res['fin_clusters'])
    if sweep:
        print('[4/5] PILLAR 3: rf sweep analysis ->', sweep)
        res['sdr_sweep'] = analyze_rtl_power(sweep)
        write_json(os.path.join(resd, 'sdr_sweep.json'), res['sdr_sweep'])
    if wav:
        print('[5/5] PILLAR 3: wav comms forensics ->', wav)
        res['sdr_wav'] = analyze_wav(wav)
        write_json(os.path.join(resd, 'sdr_wav.json'), res['sdr_wav'])
    if ledger and sweep:
        print('[6/6] PILLAR 4: cross-sensor tempo fusion')
        res['tempo'] = tempo_fusion(ledger, res.get('sdr_sweep'), res.get('sdr_wav'))
        write_json(os.path.join(resd, 'tempo_fusion.json'), res['tempo'])
    print('[*] FUSION + DOSSIER')
    summ = {'generated': UTC(), 'synthetic': synthetic,
            'pillars': sorted(res.keys()),
            'headline': {}}
    if 'osint' in res:
        summ['headline']['osint'] = {'docs': res['osint']['doc_count'],
            'priority1': sum(1 for d in res['osint']['docs'] if d['tier'] == 'PRIORITY-1'),
            'link_nodes': len(res['osint']['link_nodes'])}
    if 'fin_ledger' in res:
        summ['headline']['fin'] = {'flags': [f['kind'] for f in res['fin_ledger']['flags']],
            'clusters': res.get('fin_clusters', {}).get('cluster_count', 0)}
    if 'sdr_sweep' in res:
        summ['headline']['sdr'] = {'carriers': res['sdr_sweep']['carrier_count'],
            'ptt_pattern': sum(1 for c in res['sdr_sweep']['carriers'] if 'PTT' in c['class']),
            'ctcss': ([res['sdr_wav']['ctcss_lock']['hz']] if res.get('sdr_wav', {}).get('ctcss_lock') else [])}
    if 'tempo' in res:
        summ['headline']['tempo'] = {'coincidences': len(res['tempo']['coincidences']),
            'flags': [f['kind'] for f in res['tempo']['flags']]}
    write_json(os.path.join(resd, 'summary.json'), summ)
    render(res, os.path.join(resd, 'dossier.html'), synthetic)
    open(os.path.join(resd, 'README.md'), 'w', encoding='utf-8').write(README_TXT)
    try: shutil.copy(os.path.abspath(sys.argv[0]), os.path.join(resd, 'cartelkit.py'))
    except Exception: pass
    man = os.path.join(resd, 'MANIFEST.sha256')
    with open(man, 'w', encoding='utf-8') as fh:
        for fn in sorted(os.listdir(resd)):
            p = os.path.join(resd, fn)
            if os.path.isfile(p) and fn != 'MANIFEST.sha256': fh.write('%s  %s\n' % (sha256_path(p), fn))
    zpath = os.path.join(out, 'cartelkit_deliverable.zip')
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
        for fn in sorted(os.listdir(resd)):
            z.write(os.path.join(resd, fn), 'results/' + fn)
        tape = os.path.join(out, 'demo_tape')
        for root, _, fns in os.walk(tape):
            for fn in fns:
                p = os.path.join(root, fn)
                z.write(p, os.path.relpath(p, out))
    print('[*] ZIP: %s (sha256 %s)' % (zpath, sha256_path(zpath)[:16]))
    print(json.dumps(summ['headline'], indent=2))
    return resd

def selftest():
    ok = True
    raw = bytes(range(1, 25))
    rt = b58decode(b58encode(raw)) == raw
    print('Base58 round-trip:        %s' % ('PASS' if rt else 'FAIL')); ok &= rt
    a = segwit_addr('bc', 0, bytes(range(1, 21)))
    v1 = verify_bech32(a).get('ok') is True
    print('Bech32 valid-address:     %s   %s' % ('PASS' if v1 else 'FAIL', a))
    bad = a[:20] + ('p' if a[20] != 'p' else 'q') + a[21:]
    v2 = verify_bech32(bad).get('ok') is False
    print('Bech32 corrupted-address: %s   (correctly rejected)' % ('PASS' if v2 else 'FAIL'))
    ok &= v1 and v2
    p = b'\x00' + bytes(range(21, 41)); ck = b58encode(p + _sha256d(p)[:4])
    v3 = verify_btc_base58(ck).get('ok') is True
    print('Base58Check addr:         %s   %s' % ('PASS' if v3 else 'FAIL', ck))
    ok &= v3
    print('SELFTEST: ' + ('ALL PASS' if ok else 'FAILURES PRESENT'))
    sys.exit(0 if ok else 1)

def main():
    ap = argparse.ArgumentParser(prog='cartelkit', description='three-pillar cartel-infrastructure exploitation kit (stdlib only)')
    sub = ap.add_subparsers(dest='cmd')
    sub.add_parser('selftest')
    p = sub.add_parser('all'); p.add_argument('--out', required=True)
    p = sub.add_parser('forge'); p.add_argument('--out', required=True)
    p = sub.add_parser('osint'); p.add_argument('--dir', required=True); p.add_argument('--out', required=True)
    p = sub.add_parser('fin-validate'); p.add_argument('--addr', required=True)
    p = sub.add_parser('fin-ledger'); p.add_argument('--csv', required=True); p.add_argument('--out', required=True)
    p = sub.add_parser('fin-clusters'); p.add_argument('--jsonl', required=True); p.add_argument('--out', required=True)
    p = sub.add_parser('sdr-sweep'); p.add_argument('--csv', required=True); p.add_argument('--out', required=True)
    p = sub.add_parser('sdr-wav'); p.add_argument('--wav', required=True); p.add_argument('--out', required=True)
    p = sub.add_parser('run'); p.add_argument('--out', required=True)
    p.add_argument('--intel'); p.add_argument('--ledger'); p.add_argument('--clusters'); p.add_argument('--sweep'); p.add_argument('--wav')
    a = ap.parse_args()
    if a.cmd == 'selftest': selftest()
    elif a.cmd == 'forge':
        tape = os.path.join(a.out, 'demo_tape'); forge(tape)
        print('demo tape forged ->', tape)
    elif a.cmd == 'all':
        tape = os.path.join(a.out, 'demo_tape')
        print('[*] FORGE synthetic demo tape'); paths = forge(tape)
        run_pipeline(a.out, paths['intel'], paths['ledger'], paths['clusters'], paths['sweep'], paths['wav'])
        print('[*] DETONATION COMPLETE ->', os.path.join(a.out, 'results'))
    elif a.cmd == 'osint': write_json(a.out, scan_dir(a.dir)); print('wrote', a.out)
    elif a.cmd == 'fin-validate': print(json.dumps(validate_wallet(a.addr), indent=2))
    elif a.cmd == 'fin-ledger': write_json(a.out, analyze_ledger(a.csv)); print('wrote', a.out)
    elif a.cmd == 'fin-clusters': write_json(a.out, cluster_common_inputs(a.jsonl)); print('wrote', a.out)
    elif a.cmd == 'sdr-sweep': write_json(a.out, analyze_rtl_power(a.csv)); print('wrote', a.out)
    elif a.cmd == 'sdr-wav': write_json(a.out, analyze_wav(a.wav)); print('wrote', a.out)
    elif a.cmd == 'run':
        run_pipeline(a.out, a.intel, a.ledger, a.clusters, a.sweep, a.wav)
        print('[*] RUN COMPLETE')
    else: ap.print_help()
if __name__ == '__main__': main()