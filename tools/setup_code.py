#!/usr/bin/env python3
"""Datalog setup codes, version 1: the reference implementation of SETUP_CODE.md.

A setup code tells VAE Diagwerk for BMW-ENET which values to record in its Datalog tab, on one car. It is made from
the `datalog` section of that car's health report (JSON export). Python 3.8 or later, standard library only.

  python3 setup_code.py encode REPORT.json VALUE... [--time] [--gps] [--interval MS]
      VALUE is a module and a DID: 0x12:4807, 12:4807 or DME:4807. Prints the code.
  python3 setup_code.py decode REPORT.json CODE
      Prints the values the code picks, or why it doesn't fit the report.
  python3 setup_code.py test
      Checks this file against the test vectors in SETUP_CODE.md.

Or import it: encode(report, picks, time=False, gps=False, interval_ms=None) and decode(report, code), where
`report` is the parsed JSON and `picks` a list of (address, "DID") pairs.
"""
import binascii
import json
import math
import re
import sys

VERSION = 1
ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # Crockford's base32: no I, L, O, U
CHECK_BITS = 10
ADDRESS_BITS = 8
INTERVAL_BITS = 5
VALUE = re.compile(r"^([0-9A-F]{4})(\*?) ")


class SetupCodeError(ValueError):
    pass


# ---- The report's values ----

def modules_of(report):
    """{address: (name, common DIDs, other DIDs)} from a health report's `datalog` section: each module's values in
    the order a code counts them, its common ones (marked "*") and then the rest, each in ascending DID order."""
    datalog = report.get("datalog")
    if not datalog:
        raise SetupCodeError("the report has no datalog section (exported by an older app, or from a motorcycle)")
    if datalog.get("setupCode", {}).get("version") != VERSION:
        raise SetupCodeError("the report's setup code version isn't %d" % VERSION)
    out = {}
    for m in datalog["modules"]:
        common, other = [], []
        for v in m["values"]:
            match = VALUE.match(v)
            if not match:
                raise SetupCodeError("unexpected value line: %r" % v)
            (common if match.group(2) else other).append(match.group(1))
        out[int(m["address"], 16)] = (m["name"], sorted(common), sorted(other))
    return out


def address_of(modules, text):
    """A module given as "0x12", "12" or its name ("DME")."""
    for address, (name, _, _) in modules.items():
        if text.upper() == name.upper():
            return address
    try:
        return int(text, 16)
    except ValueError:
        raise SetupCodeError("no module %r in the report" % text)


# ---- Bits ----

class Writer:
    def __init__(self):
        self.bits = []

    def put(self, value, width):
        """[value] in [width] bits, most significant first."""
        if value < 0 or value >> width:
            raise SetupCodeError("%d doesn't fit in %d bits" % (value, width))
        self.bits.extend((value >> i) & 1 for i in range(width - 1, -1, -1))

    def gamma(self, n):
        """Elias gamma code of n >= 1: one zero less than n has bits, then n."""
        self.put(0, n.bit_length() - 1)
        self.put(n, n.bit_length())


class Reader:
    def __init__(self, bits):
        self.bits = bits
        self.at = 0

    def get(self, width):
        if self.at + width > len(self.bits):
            raise SetupCodeError("the code ends too soon")
        value = 0
        for b in self.bits[self.at:self.at + width]:
            value = (value << 1) | b
        self.at += width
        return value

    def gamma(self):
        zeros = 0
        while self.get(1) == 0:
            zeros += 1
            if zeros > 32:
                raise SetupCodeError("not a setup code")
        return (1 << zeros) | self.get(zeros)


# ---- A subset of a list, as one number (the combinatorial number system) ----

def rank_width(n, k):
    """Bits a rank of k items of n takes: enough for C(n, k) - 1 (none when there is one way)."""
    return (math.comb(n, k) - 1).bit_length()


def rank(positions):
    """The colex rank of a set of positions (0-based): the sum of C(p_i, i + 1) over them in ascending order."""
    return sum(math.comb(p, i + 1) for i, p in enumerate(sorted(positions)))


def unrank(r, k, n):
    """The k positions of rank r among n, ascending."""
    if r >= math.comb(n, k):
        raise SetupCodeError("a rank past its list")
    positions = []
    top = n
    for i in range(k, 0, -1):
        lo, hi = i - 1, top - 1  # the largest c in [lo, hi] with C(c, i) <= r
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if math.comb(mid, i) <= r:
                lo = mid
            else:
                hi = mid - 1
        positions.append(lo)
        r -= math.comb(lo, i)
        top = lo
    return sorted(positions)


# ---- The code ----

def canonical(picks, time, gps, interval_ms):
    """The setup as text, which the check is taken over: "DW1-124807-12480B-18DA12-TIME-GPS-250MS"."""
    parts = ["DW1"]
    for address, did in sorted(set(picks)):
        parts.append("%02X%s" % (address, did))
    if time:
        parts.append("TIME")
    if gps:
        parts.append("GPS")
    if interval_ms is not None:
        parts.append("%dMS" % interval_ms)
    return "-".join(parts)


def check(text):
    """The low 10 bits of the CRC-16/CCITT-FALSE of the canonical text."""
    return binascii.crc_hqx(text.encode("ascii"), 0xFFFF) & ((1 << CHECK_BITS) - 1)


def group(symbols):
    return "-".join(symbols[i:i + 4] for i in range(0, len(symbols), 4))


def encode(report, picks, time=False, gps=False, interval_ms=None):
    """The code for [picks] ((address, "DID") pairs) on the car of [report], the phone's time and GPS position, and a
    row every [interval_ms] (one of the report's `intervalsMs`; None: as often as the picks allow)."""
    modules = modules_of(report)
    intervals = report["datalog"]["intervalsMs"]
    picks = sorted({(a, d.upper()) for a, d in picks})
    if not picks and not time and not gps:
        raise SetupCodeError("nothing picked")
    w = Writer()
    w.put(int(bool(time)), 1)
    w.put(int(bool(gps)), 1)
    if interval_ms is None:
        w.put(0, 1)
    else:
        if interval_ms not in intervals:
            raise SetupCodeError("%r ms isn't one of the intervals %s" % (interval_ms, intervals))
        w.put(1, 1)
        w.put(intervals.index(interval_ms), INTERVAL_BITS)
    by_module = {}
    for a, d in picks:
        by_module.setdefault(a, set()).add(d)
    w.gamma(len(by_module) + 1)
    for a in sorted(by_module):
        if a not in modules:
            raise SetupCodeError("no module 0x%02X in the report's datalog section" % a)
        name, common, other = modules[a]
        dids = by_module[a]
        unknown = dids - set(common) - set(other)
        if unknown:
            raise SetupCodeError("%s (0x%02X) has no value %s" % (name, a, ", ".join(sorted(unknown))))
        w.put(a, ADDRESS_BITS)
        for tier in (common, other, []):  # the third: RAM values (MHD), which a report never lists
            positions = [i for i, d in enumerate(tier) if d in dids]
            w.gamma(len(positions) + 1)
            if positions:
                w.put(rank(positions), rank_width(len(tier), len(positions)))
    w.put(check(canonical(picks, time, gps, interval_ms)), CHECK_BITS)
    bits = w.bits + [0] * (-len(w.bits) % 5)
    symbols = "".join(ALPHABET[int("".join(map(str, bits[i:i + 5])), 2)] for i in range(0, len(bits), 5))
    return group(symbols)


def decode(report, code):
    """The setup [code] picks on the car of [report]: {"values": [(address, "DID")], "time", "gps", "intervalMs"}.
    Raises SetupCodeError when it doesn't fit: mistyped, or made for another car or catalog."""
    modules = modules_of(report)
    intervals = report["datalog"]["intervalsMs"]
    s = re.sub(r"[\s\-]", "", code.upper()).replace("O", "0").replace("I", "1").replace("L", "1")
    if not s or any(c not in ALPHABET for c in s):
        raise SetupCodeError("not a setup code")
    bits = [int(b) for c in s for b in format(ALPHABET.index(c), "05b")]
    r = Reader(bits)
    time = bool(r.get(1))
    gps = bool(r.get(1))
    interval_ms = None
    if r.get(1):
        index = r.get(INTERVAL_BITS)
        if index >= len(intervals):
            raise SetupCodeError("an interval past the list")
        interval_ms = intervals[index]
    picks = []
    previous = -1
    for _ in range(r.gamma() - 1):
        a = r.get(ADDRESS_BITS)
        if a <= previous or a not in modules:
            raise SetupCodeError("doesn't fit this report")
        previous = a
        _, common, other = modules[a]
        found = 0
        for tier in (common, other, []):
            k = r.gamma() - 1
            if k > len(tier):
                raise SetupCodeError("doesn't fit this report")
            if k:
                for p in unrank(r.get(rank_width(len(tier), k)), k, len(tier)):
                    picks.append((a, tier[p]))
                found += k
        if not found:
            raise SetupCodeError("not a setup code")
    want = r.get(CHECK_BITS)
    rest = bits[r.at:]
    if len(rest) >= 5 or any(rest) or (not picks and not time and not gps):
        raise SetupCodeError("not a setup code")
    if want != check(canonical(picks, time, gps, interval_ms)):
        raise SetupCodeError("the check doesn't match: mistyped, or made for another car or app version")
    return {"values": sorted(picks), "time": time, "gps": gps, "intervalMs": interval_ms}


# ---- Test vectors (SETUP_CODE.md); the app's tests hold the same ----

def _vector_report():
    """A made-up car: a DME of 3 common and 300 other values, an EGS of 2 and 40."""
    def values(common, other):
        return ["%04X* Common value %d" % (d, i) for i, d in enumerate(common)] + \
               ["%04X Value %d" % (d, i) for i, d in enumerate(other)]
    return {
        "datalog": {
            "setupCode": {"version": 1},
            "intervalsMs": [100, 150, 200, 250, 300, 400, 500, 750, 1000, 1500, 2000, 3000, 5000, 10000, 15000,
                            20000, 30000],
            "modules": [
                {"name": "DME", "address": "0x12",
                 "values": values([0x4807, 0x480B, 0x4205], [0x4000 + i * 7 for i in range(300)])},
                {"name": "EGS", "address": "0x18",
                 "values": values([0xDA12, 0x442F], [0xD000 + i for i in range(40)])},
            ],
        },
    }


VECTORS = [
    # (picks, time, gps, interval_ms, code)
    ([(0x12, "4807")], False, False, None, "114K-MAG"),
    ([(0x12, "4807"), (0x12, "480B"), (0x18, "DA12")], True, False, 250, "MDH4-XHGQ-9E"),
    ([(0x12, "4205"), (0x12, "4000"), (0x12, "4826"), (0x18, "D027")], False, True, None, "9H4G-XCVP-659Y-10"),
    ([], True, True, 1000, "X340"),
]


def _test():
    report = _vector_report()
    for picks, time, gps, interval, want in VECTORS:
        got = encode(report, picks, time, gps, interval)
        assert got == want, (picks, got, want)
        back = decode(report, got.lower().replace("-", " "))
        assert back == {"values": sorted(picks), "time": time, "gps": gps, "intervalMs": interval}, back
    # One symbol mistyped: refused but for about 1 in 1,000 (the 10-bit check; what doesn't parse is refused before it).
    tried = accepted = 0
    for *_, code in VECTORS:
        s = code.replace("-", "")
        for i in range(len(s)):
            for c in ALPHABET:
                if c != s[i]:
                    tried += 1
                    try:
                        decode(report, s[:i] + c + s[i + 1:])
                        accepted += 1
                    except SetupCodeError:
                        pass
    assert accepted * 100 < tried, (accepted, tried)
    print("ok: %d vectors; %d of %d one-symbol typos got through" % (len(VECTORS), accepted, tried))


def main(argv):
    if len(argv) >= 1 and argv[0] == "test":
        _test()
        return 0
    if len(argv) >= 3 and argv[0] in ("encode", "decode"):
        with open(argv[1], encoding="utf-8") as f:
            report = json.load(f)
        modules = modules_of(report)
        if argv[0] == "decode":
            setup = decode(report, " ".join(argv[2:]))
            for a, d in setup["values"]:
                name = modules[a][0]
                line = next(v for m in report["datalog"]["modules"] if int(m["address"], 16) == a
                            for v in m["values"] if v.startswith(d))
                print("%s 0x%02X %s" % (name, a, line))
            print("time: %s, GPS: %s, interval: %s" % (setup["time"], setup["gps"],
                                                       "%d ms" % setup["intervalMs"] if setup["intervalMs"] else "as fast as the picks allow"))
            return 0
        picks, time, gps, interval = [], False, False, None
        args = iter(argv[2:])
        for arg in args:
            if arg == "--time":
                time = True
            elif arg == "--gps":
                gps = True
            elif arg == "--interval":
                interval = int(next(args))
            else:
                module, _, did = arg.partition(":")
                picks.append((address_of(modules, module), did.upper()))
        print(encode(report, picks, time, gps, interval))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except SetupCodeError as e:
        print("setup code: %s" % e, file=sys.stderr)
        sys.exit(1)
