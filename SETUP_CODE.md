# Datalog setup codes

**VAE Diagwerk for BMW-ENET** records live values in its **Datalog** tab: the values a person picks, from the modules
of their car, a row at a time into a CSV file. A **setup code** picks them for the person: a short code like
`MDH4-F9AC-4RRC-0ZB0` that they enter in the app (**Datalog › Setup code › Enter a code › Pick these values**). The app
then picks those values, the phone's clock or GPS position if the code asks, and the save interval, and says by name
what it picked.

This page is for an AI assistant helping someone with a car: how to choose values from a health report and give the
person a setup code for them. The health report's JSON (**Health report › Export › JSON**) lists what the car can
record in its `datalog` section; [GUIDE.md](GUIDE.md) describes the rest of the file.

## When to offer one

When live values would answer the question better than the fault memory can: a boost or fuel complaint, a temperature
that runs high, a fault that only shows under load, checking a repair. Say which values you picked and why, what to do
while recording (a third-gear pull from 2,000 rpm, a 20-minute drive, idle until the fan runs), and give the code.

- **Pick few values.** A module answers its values one after another, so every value picked on a module makes its
  rows slower. Four to ten values a module keeps a row every 100 to 250 ms; dozens make it seconds.
- **Prefer the common values** (marked `*`) when they answer the question: they are what people log most, and they
  make the code shorter (about 4 bits each, against about 10 to 11 for the others).
- **Pick from this car's report only.** A code counts places on the car's lists of values, so it fits the car the
  report was made on, read by the same app version. If the person updated the app since, or the code is for another
  car, the app refuses it. It never picks other values. Ask for a new report then.
- **Don't promise a value answers.** Many values change only with the engine running, and a module may refuse a value
  in its current state. The app drops those from the log and says so.
- **Units are metric** in the log, whatever the person's display units.

## What the report gives

```
datalog {
  about
  setupCode   { version, guide }        version: 1, the format on this page
  intervalsMs [100, 150, 200, … 30000]  the save intervals a code can ask for
  modules[]   { name, address, values[] }
}
```

`address` is the module's diagnostic address as hex text (`"0x12"`). Each of `values` is one line:

```
4807* Engine speed (rpm)
4AB0* Boost pressure, target (hPa)
4000 Engine measured values: Lambda controller 1; Lambda controller 2; Vehicle speed (km/h); …; and 16 more
```

The four hex digits are the value's DID. A `*` after them marks a common value. Then the value's name and its unit, or,
for a value made of several readings, those readings after a colon (the first eight, and how many more). Picking such a
value records all its readings. Match a line with `^([0-9A-F]{4})(\*?) (.*)$`. The common values come first, then
the rest, each in DID order.

A report without a `datalog` section (an older app version, or the Motorrad app) can't give a code. Tell the person
which values to pick by name instead (each module's card in the Datalog tab has a search).

## Making the code

**Run the reference implementation**, [`tools/setup_code.py`](tools/setup_code.py) (Python 3.8 or later, standard
library only; raw file at
`https://raw.githubusercontent.com/vandelayautollc/diagwerk-health-report/main/tools/setup_code.py`):

```
python3 setup_code.py encode report.json DME:4807 DME:4AB0 DME:4205 EGS:DA12 --time --interval 250
python3 setup_code.py decode report.json MDH4-F9AC-4RRC-0ZB0
```

A value is its module (name, or address: `0x12`, `12`) and its DID. `--time` adds the phone's clock (UTC), `--gps`
its position, `--interval MS` a row every MS milliseconds (one of `intervalsMs`; left out, the app saves rows as often
as the picks allow). `decode` lists what a code picks: run it on your code before you give it.

If you can only run code you write, this is the whole encoder; check it against the [test vectors](#test-vectors)
before using it:

```python
import binascii, math

ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

def setup_code(report, picks, time=False, gps=False, interval_ms=None):
    """picks: [(address, "DID")], e.g. [(0x12, "4807")]. Returns the code, e.g. "114H-38N"."""
    datalog = report["datalog"]
    tiers = {}
    for m in datalog["modules"]:
        common = sorted(v[:4] for v in m["values"] if v[4] == "*")
        other = sorted(v[:4] for v in m["values"] if v[4] != "*")
        tiers[int(m["address"], 16)] = (common, other, [])  # the third: RAM values, never in a report
    bits = []
    def put(value, width):
        bits.extend((value >> i) & 1 for i in range(width - 1, -1, -1))
    def gamma(n):  # Elias gamma, n >= 1
        put(0, n.bit_length() - 1)
        put(n, n.bit_length())
    picks = sorted({(a, d.upper()) for a, d in picks})
    put(int(time), 1)
    put(int(gps), 1)
    if interval_ms is None:
        put(0, 1)
    else:
        put(1, 1)
        put(datalog["intervalsMs"].index(interval_ms), 5)
    modules = sorted({a for a, _ in picks})
    gamma(len(modules) + 1)
    for a in modules:
        dids = {d for b, d in picks if b == a}
        assert dids <= set(tiers[a][0]) | set(tiers[a][1]), "a DID the module doesn't list"
        put(a, 8)
        for tier in tiers[a]:
            positions = [i for i, d in enumerate(tier) if d in dids]
            gamma(len(positions) + 1)
            if positions:
                rank = sum(math.comb(p, i + 1) for i, p in enumerate(positions))
                put(rank, (math.comb(len(tier), len(positions)) - 1).bit_length())
    text = "-".join(["DW1"] + ["%02X%s" % p for p in picks] + (["TIME"] if time else []) +
                    (["GPS"] if gps else []) + (["%dMS" % interval_ms] if interval_ms is not None else []))
    put(binascii.crc_hqx(text.encode("ascii"), 0xFFFF) & 0x3FF, 10)
    bits += [0] * (-len(bits) % 5)
    s = "".join(ALPHABET[int("".join(map(str, bits[i:i + 5])), 2)] for i in range(0, len(bits), 5))
    return "-".join(s[i:i + 4] for i in range(0, len(s), 4))
```

**Don't work a code out by hand** or guess one. The check makes the app refuse it. If you can't run code, give the
values by name.

In the demo car's report ([`examples/demo-car-report.json`](examples/demo-car-report.json)), the DME's engine speed
alone is `114H-38N`. The DME's charging pressure, engine speed, accelerator pedal position, boost target, intake
manifold pressure and charge air temperature, the EGS's engine torque and transmission oil temperature, the phone's
time and a row every 250 ms come to `MDH4-F9AC-4RRC-0ZB0`.

## Giving it to the person

Give the code on its own line, as the app writes it (groups of four with dashes; case and dashes don't matter to the
app). Tell them where it goes: **Datalog › Setup code › Enter a code › Pick these values**. The code replaces what
they had picked. The app then lists what it picked; ask them to check it matches what you meant.

If the app says **"That code doesn't fit this car"**, either the code was mistyped or the report is out of date (made
on another car, or before the app was updated). Ask them to retype it, or to export a new report and send it to you.

## The format, version 1

For anyone writing their own encoder or decoder. The bits, most significant first:

| Bits | What |
| --- | --- |
| 1 | The phone's time (TIME) |
| 1 | The phone's GPS position (GPS) |
| 1 | An interval is set |
| 5 | If set: its index in `intervalsMs` (0-based) |
| γ | The number of modules plus one |
| per module, ascending address: | |
| 8 | The module's address |
| per tier (common, other, RAM): | |
| γ | The number of values picked in that tier plus one |
| w | If any: the rank of their positions, in w = bit length of C(n, k) − 1 bits (n the tier's size, k picked; 0 bits when C(n, k) = 1) |
| 10 | The check |
| 0–4 | Zero bits up to a whole symbol |

- **Tiers.** A module's values in three lists: its common values (`*`), its other values, each in ascending DID order,
  and its RAM values (values the MHD tuning software logs, which the app reads from the engine's memory only once it
  has found MHD on the car; never listed in a report, so a code made from one always has none there). Every module of
  the code writes all three, an empty one as a single `1` bit.
- **γ** is the Elias gamma code of n ≥ 1: as many `0` bits as n has bits less one, then n in binary.
- **The rank** of positions p₁ < p₂ < … < pₖ (0-based, within the tier) is ∑ C(pᵢ, i), i from 1 to k: the
  combinatorial number system (colex order). It is below C(n, k).
- **The check** is the low 10 bits of the CRC-16/CCITT-FALSE (polynomial 0x1021, initial value 0xFFFF, no reflection;
  Python's `binascii.crc_hqx(data, 0xFFFF)`) of the setup as ASCII text: `DW1`, each value as its module's address in
  two hex digits and its DID (in order of address and then DID), `TIME`, `GPS`, the interval in ms followed by `MS`,
  joined by dashes: `DW1-124205-124807-18DA12-TIME-250MS`. Because the check covers what the code means rather than its
  symbols, a code read against a different list of values is refused, as is all but about 1 in 2,000 mistyped codes.
- **Symbols.** Crockford's base32 (`0123456789ABCDEFGHJKMNPQRSTVWXYZ`), five bits each, in groups of four joined by
  `-`. Reading, ignore case, spaces and dashes; read `O` as `0` and `I` or `L` as `1`.
- **Reading** a code also refuses one whose module addresses aren't ascending, that names a module or rank the list
  doesn't have, picks nothing on a module it names, picks nothing at all, or has five or more bits, or any `1` bit,
  after the check.

### Test vectors

A made-up car: a DME (`0x12`) whose common values are `4205`, `4807` and `480B` and whose other values are `4000` +
7·i in hex for i from 0 to 299 (`4000`, `4007`, `400E`, … `482D`); an EGS (`0x18`) whose common values are `442F` and
`DA12` and whose other values are `D000` to `D027`. With the intervals `[100, 150, 200, 250, 300, 400, 500, 750, 1000,
1500, 2000, 3000, 5000, 10000, 15000, 20000, 30000]`:

| Picks | Code |
| --- | --- |
| DME 4807 | `114K-MAG` |
| DME 4807, 480B; EGS DA12; TIME; 250 ms | `MDH4-XHGQ-9E` |
| DME 4000, 4205, 4826; EGS D027; GPS | `9H4G-XCVP-659Y-10` |
| TIME, GPS; 1000 ms | `X340` |

`python3 tools/setup_code.py test` checks the reference implementation against them. The app's own tests hold the same
vectors.
