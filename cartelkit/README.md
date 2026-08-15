CARTELKIT v1.0 -- three-pillar cartel-infrastructure exploitation kit
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
