# Reading a VAE Diagwerk health report

This guide is for an AI assistant (or any program) that has been handed a JSON file whose `schema` is
`vae-diagwerk-health-report/1`. It says what the file is, what each key holds, and the BMW- and app-specific background
you need to read it correctly. It is self-contained: you don't need anything else from this repository.

- [What the file is](#what-the-file-is)
- [Six things to get right](#six-things-to-get-right)
- [Layout](#layout)
- [How values are written](#how-values-are-written)
- [BMW background](#bmw-background)
- [App specifics](#app-specifics)
- [Analyzing a report](#analyzing-a-report)
- [Versions](#versions)

## What the file is

**VAE Diagwerk** is a family of phone apps (Android and iOS, by Vandelay Auto Electronics) that read BMW vehicles
through the diagnostic port:

- **VAE Diagwerk for Motorrad** reads BMW Motorrad motorcycles and scooters from model year 2018 on.
- **VAE Diagwerk for BMW-ENET** reads BMW cars of the F-series generation (and the MINI and Rolls-Royce models built on
  them) over an ENET (Ethernet) cable.

Both apps' **health report** walks every control module on the vehicle and collects each one's fault memory and a few
other things the module keeps. Both write it in this layout. `app` says which app made the file, and `about` which
kind of vehicle it is. Where this guide describes something only one of them has, it says **Motorrad** or **cars**.

The person exported that report as JSON to hand it to you, usually to ask "what is wrong with this vehicle?", "what
should I fix first?" or "should I buy it?".

The report is a snapshot of what the modules reported at one moment (`readAt`). It is the same content as the app's PDF
report, as data.

## Six things to get right

1. **Values are display text, not numbers.** `"42,509 mi"`, `"14.25 V"`, `"68.5 °F"`. The unit system (metric or
   imperial) is whatever the person's app is set to. See [How values are written](#how-values-are-written).
2. **A missing key means "not in this report", not "no" or "zero".** The file never carries placeholders. A fault
   without `snapshots` may have none stored, or the report may have been made without them (see
   [App specifics](#app-specifics)).
3. **`faultMemoryRead: false` means unknown, not clean.** That module's faults could not be read. Only a module with
   `faultMemoryRead: true` and an empty `faults` list has no faults.
4. **`stored` is not `active`.** A stored fault was recorded at some point and is not confirmed present right now. See
   [Active and stored](#active-and-stored).
5. **A BMW fault code is not an OBD-II code.** `3A1460` is BMW's own numbering. Use the `description` in the file. If
   a fault has no `description`, say that you don't know what the code means rather than guessing. See
   [Fault codes](#fault-codes).
6. **`(demo)` in `app` means a simulated vehicle.** Each app has a demo mode with a made-up vehicle. Its report is not
   a real vehicle's and its numbers don't form a consistent history. If you are asked to analyze one, say so first, then
   go on if the person wants it read as an illustration.

## Layout

```
schema, guide, about, app, readAt
vehicle   { title, details[] }
summary   { activeFaults, storedFaults, modules, modulesNotRead }
modules[] { name, controlUnit, status, faultMemoryRead, note?, software[]?, values[], fscEntitlements[]?, faults[]? }
  faults[] { code, description?, status, area?, occurred?, details?, snapshots[]? }
options[] { code, description?, listedBy? }        (only when the vehicle order was read)
notes[]
```

A `?` marks a key that is left out when there is nothing to say.

### Top level

| Key | Holds |
| --- | --- |
| `schema` | `"vae-diagwerk-health-report/1"`. See [Versions](#versions). |
| `guide` | The address of this guide. Older exports don't have it. |
| `about` | One sentence on what the file is. |
| `app` | The app and version that made the report: `"VAE Diagwerk for Motorrad v0.4.3"`, `"VAE Diagwerk for BMW-ENET v0.1.1"`. Ends in `" (demo)"` for the simulated vehicle. |
| `readAt` | When the vehicle was read, ISO 8601 in UTC: `"2026-11-11T13:36:14Z"`. |
| `vehicle` | What vehicle this is. |
| `summary` | Counts over the whole report (numbers). |
| `modules` | One entry per control module found on the vehicle. The substance of the report. |
| `options` | The vehicle's option codes. Left out when the vehicle order could not be read. |
| `notes` | The report's footnotes, as sentences. |

### `vehicle`

`title` is the short name: `"2019 R 1250 GS"` (Motorrad), `"2017 F30"` (cars: production year and model series).
`details` is a list of `{label, value, note?}`.

Motorrad:

| `label` | `value` | `note` |
| --- | --- | --- |
| `Model` | `"R 1250 GS"` | BMW's type key and series code, `"0J93 · K50"`. The type key is characters 4 to 7 of the VIN and names the exact model variant; the series code (K50, K51, K82…) is BMW's internal name for the model family. |
| `Year` | Model year, `"2019"` | Production month, `"May 2019"`. |
| `Odometer` | The instrument cluster's odometer, `"42,509 mi"` | |
| `VIN` | The vehicle identification number | |

Cars:

| `label` | `value` | `note` |
| --- | --- | --- |
| `Model series` | BMW's development code for the model, `"F30"` (3 Series sedan), `"F56"` (MINI hatch) | BMW's type code, `"Type code 8B73"`: four characters naming the exact variant (engine, body, drive, market), from the vehicle order. |
| `Year` | Production year, `"2017"` | Production month, `"Mar 2017"`. |
| `Software level` | The car's integration level (BMW: I-step), `"F020-19-11-520"`: the BMW software release it was last programmed to, as model family, year, month and a number. See [Software versions](#software-versions). | |
| `VIN` | The vehicle identification number | |

A value the app could not learn reads `"Unknown"`. A car report has no odometer: the car app doesn't read the
mileage yet.

### `summary`

`activeFaults` and `storedFaults` are totals over all modules. `modules` is how many modules the report lists and
`modulesNotRead` how many of those have `faultMemoryRead: false`. If `modulesNotRead` is not 0, the fault totals are
incomplete: say so.

### `modules[]`

| Key | Holds |
| --- | --- |
| `name` | Motorrad: what the module does, in the app's words: `"Engine"`, `"ABS"`, `"Instrument cluster"`. Cars: BMW's short name for the module: `"DME"`, `"DSC"`, `"KOMBI"`. See [Control modules](#control-modules). |
| `controlUnit` | BMW's name for this module variant and its diagnostic address: `"X_BMS-O @ 0x12"`, `"DME8FF_R @ 0x12"`. |
| `status` | The module's fault count as text: `"2 active · 3 stored"`, `"5 active"`, `"2 stored"`, `"No faults"`, `"Not read"`. |
| `faultMemoryRead` | `true` when the fault memory was read. `false`: see `note`. |
| `note` | Why the fault memory was not read. See [Modules that were not read](#modules-that-were-not-read). |
| `software` | Cars: the module's software parts, `{part, id, version}`. See [`software[]`](#software). Left out when the module didn't report them. |
| `values` | Other things the module keeps, as `{label, value, flag?, usageStatistic?}`. May be empty. |
| `fscEntitlements` | Paid software features enabled in this module. See [FSC entitlements](#fsc-entitlements). |
| `faults` | The module's faults. Present (possibly empty) only when `faultMemoryRead` is `true`. |

A module whose fault memory was not read can still have `values`: those are read separately.

#### Modules that were not read

| `note` | What happened |
| --- | --- |
| `Fault memory not read: refused (…)` | The module answered and declined the request; the name in brackets is its reason code. `serviceNotSupported` usually means this module variant doesn't offer the fault-memory request the app uses: a limit of the reading, not a symptom, and reading again won't change it. |
| `Fault memory not read: didn't answer` | The module was found and then went quiet. A loose cable, a weak battery or a module problem. On a car, some modules (the transmission's, the gear selector's) go to sleep or answer only with the ignition fully on; reading again with the ignition on may help. |
| `Fault memory not read: fault list not readable` | The reply wasn't in a form the app understands. |
| `The connection dropped before this module was read.` | The reading was cut short. The modules after this point are all unread; the report should be made again. |

In every case the module's faults are unknown. Don't count it as clean and don't count it as faulty.

#### `software[]`

Cars only. The module's software parts as its own software list (BMW: SVK) reports them, in its order:
`{"part": "SWFL", "id": "00003076", "version": "090.060.006"}`.

| Key | Holds |
| --- | --- |
| `part` | BMW's process class of the part. `SWFL` (software flash): the module's program. A module can have more than one. |
| `id` | The part's number in BMW's software catalog (SGBM number), eight hex digits. |
| `version` | Its version, main.sub.patch, three digits each. |

The same module type on another car can run another part or version. See [Software versions](#software-versions)
for what the numbers tell you and what they don't.

#### `values[]`

| `label` | Meaning |
| --- | --- |
| `Odometer` | Motorrad. The vehicle's odometer, on the instrument cluster. |
| `Odometer stored` | Motorrad. The mileage this module keeps for itself. See [Odometer copies](#odometer-copies). |
| `VIN` | Motorrad. The VIN stored in this module. `flag: "Differs"` when it is not the vehicle's. See [VIN copies](#vin-copies). |
| `Next service in` | Motorrad. Distance left to the next service as this module keeps it: `"6,214 mi"`, or `"Overdue by 1,200 km"`. |
| `Next service due` | Motorrad. Date of the next service as this module keeps it: `"Oct 10, 2027"`, with `" (overdue)"` when past; `"Off"` (date reminder switched off); `"Not set"`. |
| `Highest engine speed` | Motorrad usage statistic. The highest engine speed the engine module has recorded. |
| `Times over 9,500 rpm` | Motorrad usage statistic. How often the engine went over its over-rev limit. The limit in the label is that engine's and differs by model. |
| `Last time over 9,500 rpm` | Motorrad usage statistic. The mileage of the latest over-rev: `"At 25,652 mi"`. |
| `Time leaned 60° or more` | Motorrad usage statistic. Total time the ABS module has counted at a lean angle of 60° or more. |
| `FSC entitlements` | Only as a status: `"None active"`, or `"Not read: …"` with the reason. The entitlements themselves are in `fscEntitlements`. |

Usage statistics carry `"usageStatistic": true`. See [Usage statistics](#usage-statistics). A car report has only the
`FSC entitlements` status so far. Later app versions may add labels; treat one you don't know as what its text says.

#### `faults[]`

| Key | Holds |
| --- | --- |
| `code` | BMW's fault code, six hex digits: `"3A1460"`. |
| `description` | What the fault is. Left out when the app has no text for the code. |
| `status` | `"active"` or `"stored"`. |
| `area` | Motorrad. BMW's function group for the fault: `"Exhaust flap 1"`, `"Fuel filler cap lock"`. For a network fault, `"CAN bus"` and, when known, the sender of the missing message: `"CAN bus · Sensor box"`. Left out when the app has none, which on a car is always, so far. |
| `occurred` | A one-line summary: the OBD code if the fault has one, the mileage of the first occurrence, and the occurrence count: `"P0078 · 42,996 mi · 27× occurrences"`. When the latest occurrence was at another mileage, the range: `"37,755–42,441 mi"`. Each part only when known; left out when none is. |
| `details` | The fault's counters, by name. See below. Left out when the module gave none. |
| `snapshots` | The records the module saved when the fault occurred. See [Snapshot records](#snapshot-records). Left out when the report has none for this fault. |

`area` uses BMW's group names, and a group's numbering doesn't tell you the side or cylinder: `"Exhaust flap 1"` sits
beside a description that says "right". Go by the description.

`details` can hold:

| Name | Meaning |
| --- | --- |
| `OBD code` | The standard OBD-II code the module reports for this fault (`"P0476"`, sometimes with a two-digit failure type, `"P0476-1F"`). Mostly on emissions-related engine faults. |
| `Occurrences` | How many times the module has counted the fault occurring. A one-byte counter: it cannot go past 255. |
| `Healing counter` | The module's counter toward dropping a fault that has stopped occurring. See [Counters](#counters). |
| `Fault class` | BMW's urgency for the fault: `"Check at next service"`, `"Check at next stop"` or `"Check right away"`. |
| `Warning light` | `"Requested"`: the module is asking for a warning light or message because of this fault. |

Each is there only when the module gave it.

`snapshots` is a list of `{record, readings}`. `record` names the record and its mileage. The first is always
`"First occurrence · 37,755 mi"`. With two records the second is `"Latest occurrence · 42,441 mi"`. A module that
keeps more numbers the rest, `"Snapshot 2 · …"`, `"Snapshot 3 · …"`, in the module's own order, which the app
doesn't interpret further: don't assume the highest number is the latest.

`readings` maps a reading's name to its value at that moment:
`{"Battery voltage": "13.2 V", "Engine speed": "0 rpm"}`. Which readings there are depends on the module and the fault.

### `options[]`

The vehicle order: the factory options and registered retrofits, as BMW option codes. `{code, description?, listedBy?}`:
`{"code": "193", "description": "Keyless Ride"}`, `{"code": "2VB", "description": "Tire pressure monitor"}`.
`description` is BMW's name for the code (from its workshop system) and is left out when the app has no name for it.
`listedBy` is explained under [Options](#options).

### `notes[]`

Sentences from the report's footer. Typically: `"Read with <app> on Nov 11, 2026, 8:36 AM."` (in the phone's local time;
use `readAt` for the exact moment); `"VIN mismatch"` when a module holds another VIN; the usage statistics caveat when
the report has any; and the disclaimer that the values come with no guarantee and don't replace an inspection.

## How values are written

- **Text with units.** Parse a number out only if you need to calculate; otherwise quote the value as it is.
- **Thousands separators are commas, the decimal mark is a point**: `"42,509 mi"`, `"1,250 rpm"`, `"14.25 V"`.
- **A percent sign and a bare degree sign (an angle) are attached**: `"20.5%"`, `"12°"`. Every other unit follows a
  space, temperatures included: `"68.5 °F"`.
- **Units follow the app's setting.** Metric: km, km/h, °C, bar, hPa, L, N·m, mm. Imperial: mi, mph, °F, psi, gal,
  lb·ft, in. One report uses one system throughout. The vehicle stores everything in metric; imperial values are
  converted and rounded, so a mileage in miles can differ by a mile from what the dash shows.
- **Ranges use an en dash**: `"60,760–68,302 km"`.
- **Dates** are written out: `"Oct 10, 2027"`. Only `readAt` is ISO 8601.
- **Other values**: a plain number for a reading without a unit (`"1.00"` for a lambda factor, `"1"` for a mode
  number), `"Yes"` / `"No"`, `"On"` / `"Off"`, a word from the module's own table of states, and now and then a hex
  number (`"0x01A2"`) for a raw value. Identifiers are hex too: `swid` `"0x018F"`, the address in `controlUnit`, a
  software part's `id`.

## BMW background

### Control modules

A BMW is a network of control modules (ECUs), each with its own fault memory. There is no single "the vehicle's fault
list": a problem in one place usually shows up in several modules' memories.

#### On a motorcycle

The modules share a CAN bus. `name` is the app's plain name for the module's job. The ones you will meet:

| `name` | What it is | `controlUnit` starts with |
| --- | --- | --- |
| Engine | Engine control (fuel, ignition, throttle, riding modes, traction control logic) | `X_BMS` |
| ABS | Integral ABS: brakes, wheel speed, ABS Pro, hill start control | `X_IABS` |
| Instrument cluster | The dash (TFT or analog); keeps the odometer and the service reminder | `X_KOMBI` |
| Body controller | Central electronics: lights, horn, heated grips, power distribution | `X_BCO`, `X_BCL` |
| Central computing | On the newest models, the central computer and gateway | `X_CCP` |
| Tire pressure | Tire pressure monitor (BMW: RDC) | `X_RDC` |
| Suspension (ESA) | Electronic suspension adjustment | `X_ESA` |
| Suspension (DSA) | Semi-active suspension (Dynamic ESA) | `X_SAF` |
| Keyless ride | Keyless ignition, steering lock, fuel cap lock | `X_SLZ` |
| Immobilizer | Electronic immobilizer (BMW: EWS), on vehicles without Keyless Ride | `X_EWS` |
| Alarm | Anti-theft alarm (BMW: DWA) | `X_DWA` |
| Transmission | Automated shift assistant | `X_TCU` |
| Radar, Radar (side/short) | Front radar for active cruise control; side and short-range radar | `X_MRR`, `X_SVA`, `X_SRR` |
| Adaptive headlight | Cornering headlight | `X_ASW` |
| Telematics | ConnectedRide, emergency call | `X_TPM`, `X_WAVE` |
| Audio | Audio system | `X_AP`, `X_AUDIO` |
| Authority module | Extra body controller on police and other authority vehicles | `X_BCA` |
| HV battery, Battery control, Battery management, DC-DC converter, Drive electronics | Electric models (CE 04, CE 02): high-voltage battery, charging and drive | `X_SME`, `X_BSK`, `X_BMU`, `X_DCDC`, `X_AE` |

A module the app has no name for is named by its address (`"0x4A"`).

`controlUnit` is what BMW's own workshop software calls the module variant, then `@` and the module's diagnostic
address. The part after the dash distinguishes variants and often hints at the supplier and generation
(`X_IABS-CONTM100`, `X_BCL-LEAR01`). It is useful when someone looks the fault up in BMW documentation or orders a
part; you rarely need it for the analysis.

Which modules a vehicle has depends on model and options. A module missing from the report is normally just not
fitted. A module that is fitted but dead may not appear either; the sign of that is other modules reporting its
messages missing. Don't infer a missing module from the options list: many options have no module of their own.

Not everything on the bus is a module with a fault memory. The **sensor box** in particular never appears in `modules`;
you learn about it only from the modules that listen to it.

#### On a car

An F-series car has 15 to 40 modules on several buses (CAN networks, FlexRay, Ethernet), all reached through one
**central gateway**, the module the diagnostic cable talks to. `name` is BMW's own short name for the module, and
`controlUnit` names the variant as BMW's workshop software does (`DME8FF_R`, `DSC_25`, `NBTEVO`), then its address.
The ones you will meet most:

| `name` | What it is |
| --- | --- |
| FEM, BDC | Front electronic module or body domain controller: the central gateway (address 0x10), and as a second address the body controller (lights, locking, wipers, power distribution: FEM-B, 0x40). One physical unit. |
| DME, DDE | Engine control, petrol or diesel. DME2: the second bank of a V8 or V12. |
| EGS | Automatic transmission control. |
| DSC | Dynamic stability control: ABS, traction and stability control, brake functions. |
| EPS | Electric power steering. |
| ICM | Integrated chassis management: vehicle dynamics, coordinates DSC, steering and suspension. |
| ACSM | Crash safety module: airbags and belt tensioners. |
| KOMBI | Instrument cluster: the dash, Check Control messages, the odometer. |
| HU | Head unit: navigation, media, phone (NBT, NBT Evo, Entry Nav, CIC). |
| REM, JBBF | Rear electronics or junction box: rear lights, trunk, power distribution. |
| IHKA | Automatic climate control. |
| FZD | Roof function center: interior lights, sunroof, emergency call buttons. |
| TCB, ATM | Telematics: emergency call, ConnectedDrive. |
| LMV | xDrive transfer case. |
| VDC | Adaptive dampers. |
| KAFAS | Camera-based driver assistance: lane departure, speed-limit info, collision warning. |
| TRSVC | Reversing and surround-view cameras. |
| FRR | Front radar for active cruise control. |
| FLE-L, FLE-R | Headlight electronics, left and right. |
| SM, SMBF | Seat modules, driver and passenger. |
| ZBE | iDrive controller. |
| GWS | Gear selector. |
| AMP, ASD | Audio amplifier; active sound design. |
| PDC, PMA | Park distance control; parking assistant. |
| RDC | Tire pressure monitor. |
| EME, SME, LIM | Electric and plug-in hybrid models: electric-motor electronics, high-voltage battery, charging. |

A module the app has no name for is named by its address (`"0x4A"`). As on a motorcycle, a module missing from the
report is normally not fitted, and one that is fitted but dead shows up as other modules reporting it missing.

Terms that show up in descriptions and readings:

| Term | Meaning |
| --- | --- |
| Sensor box | The inertial measurement unit (lean angle, acceleration, yaw). ABS Pro, traction control and semi-active suspension depend on it. |
| Terminal 15 | Switched ignition power (German *Klemme 15*). "Terminal 15 voltage" is the supply voltage with the ignition on. |
| Check Control message | Cars: a warning or notice the instrument cluster shows the driver, with a number (CC-ID). A fault that records one ("Check Control message (ID 2064): engine oil service due") says that the message was shown. It can be a notice (service due, washer fluid low), not a defect: read its text. |
| I-step | Cars: integration level, the BMW software release the whole car was programmed to (`"F020-19-11-520"`). |
| Terminal 30 | Permanent battery power. |
| Output stage | The driver circuit in a module that powers an actuator. "Output stage, open circuit" is about the wiring or the actuator on that output as much as about the module. |
| DTC | In BMW Motorrad feature names, **Dynamic Traction Control**, not "diagnostic trouble code". An entitlement named `DTC` is the traction control feature. |
| ASC, DTC, MSR, HSC, DBC | Rider aids: stability control, traction control, engine drag torque control, hill start control, dynamic brake control. |
| ESA, DSA, Dynamic ESA | Electronically adjusted and semi-active suspension. |
| RDC | Tire pressure monitoring. |
| EWS | Immobilizer. |
| ShiftCam | The boxer engine's variable intake cam system. |
| Gearshift assistant | The quickshifter. |
| Lambda | Air-fuel ratio relative to stoichiometric; 1.00 is ideal. Oxygen-sensor readings are in lambda. |
| Exhaust flap | A valve in the exhaust that the engine module moves with an actuator motor. |
| (raw), (linearized) | In a reading's name: the sensor's value before or after the module's correction. |
| (calculated), (modeled) | In a reading's name: a value the module computes instead of measuring. |

Descriptions and reading names also carry BMW-internal abbreviations this guide doesn't list. Quote one you don't
know as it stands instead of expanding it.

### Fault codes

BMW modules number their faults with BMW's own six-hex-digit codes (`3A1460`, `D3542C`, `480904`). These are not the
OBD-II P-codes a generic scanner shows, and public lists of them are unreliable: the same number means different things
in different modules and module variants, between cars and motorcycles too. Always read a code together with its
module, and rely on the `description` in the file.

`description` is the app's wording of BMW's fault text for that code in that module. It names the component and the
kind of failure, in a fixed pattern: *component, what is wrong*. The usual failure kinds:

| Wording | Means |
| --- | --- |
| open circuit | No electrical connection: unplugged, broken wire, failed actuator coil. |
| short circuit to ground / to battery voltage | The wire or component is shorted. |
| implausible signal | The value doesn't fit what other signals say. |
| timeout (of a CAN message) | An expected message from another module stopped arriving. |
| deactivated due to… / limited operation | A function switched itself off because of something it depends on. A consequence, not a cause. |

When `description` is missing, the app has no text for that code. Report the code, module, status and whatever
`area`, `details` and `snapshots` say, and state that the meaning isn't known.

Engine faults that matter for emissions also carry a standard `OBD code`. That one is a real OBD-II code and can be
looked up, but BMW's description is more specific than the generic OBD meaning.

### Active and stored

- **`active`**: the module's check for this fault is failing now, in the current ignition cycle.
- **`stored`**: the fault is in memory but not confirmed present now. Either it has gone away, or the module hasn't
  run that check yet since the ignition was switched on.

The second case matters. Reports are usually read with the ignition on, the engine off and the vehicle standing.
Many checks only run with the engine running or the wheels turning, so a fault that is still there can read `stored`.
The opposite also happens: battery voltage sagging during a long session with the ignition on can itself set faults.

The mileage of an active fault is when it was first stored, not when it was last seen. An active fault first stored
long ago has either been there since or has come back.

A stored fault stays in memory until the module drops it after a long fault-free spell or someone clears the memory.
One stored fault from thousands of kilometers ago with one occurrence is history. A stored fault with many
occurrences at the current mileage is a live intermittent problem.

Fault memories can be cleared with any diagnostic tool, this app included. A clean report shows that nothing is
stored now; it doesn't show that nothing ever was.

### Counters

- **Occurrences**: how many times the fault has been detected anew. High counts mean an intermittent fault
  (a loose connector, chafed wire, marginal sensor). The counter stops at 255.
- **Healing counter**: BMW's *Heilungszähler*. The module uses it to decide when a fault that no longer occurs can be
  dropped from memory; it changes with each drive cycle in which the fault stayed away. Start value and direction
  differ between modules and the report doesn't say which applies, so leave it out of your analysis. Use status,
  occurrences and mileage to judge how current a fault is.
- **Fault class** and **Warning light**: how urgent BMW rates the fault and whether the module is asking for a warning
  to the rider. Not every module stores a fault class; its absence says nothing.

### Snapshot records

When a module stores a fault it saves a freeze frame: the mileage and a handful of readings at that moment. BMW calls
these *Umweltbedingungen* (environmental conditions). Modules keep the first occurrence and usually the latest, and
some keep more.

- Readings are **from the moment the fault was stored, not current values**.
- The mileage in `record` (and in the fault's `occurred`, which is taken from the records) is the best evidence of
  when a fault happened. Compare it with the odometer.
- **A mileage of 0 usually means the module didn't have a mileage** when it stored the fault. Treat it as unknown,
  not as "happened at 0". The same goes for `"0 mi"` or `"0 km"` in `occurred`.
- **A fault can have a mileage and no `snapshots`.** The module's record then held nothing but the mileage, or no
  reading the app can decode. Only records with readings are listed.
- The readings tell you the circumstances. `Engine speed` 0 with `Vehicle speed` 0: standing, engine not running
  (`Time since engine start` is then 0 too). A running engine with a small `Time since engine start`: right after
  start-up. Several faults at one mileage with the engine not running were probably stored together, at one
  switch-on.
- `Battery voltage` shows whether supply voltage was involved. Well under 12 V with the engine off, or a dip during
  cranking, explains many otherwise unrelated faults stored at the same mileage. Around 14 V with the engine at 0 rpm
  points to a charger or external supply, or to an engine that had just stopped.
- A record is saved when the module confirms the fault, which can be seconds after the event. A fall-detection record
  showing a stopped engine doesn't mean the engine was off before the vehicle went over.
- A reading of the failed component itself is often the faulty or a substitute value, not a real measurement. Some
  readings are placeholders for "no measurement": a temperature at absolute zero (`"-459.7 °F"`, about −273 °C), or an
  implausible value that repeats unchanged across records and sensors. Don't diagnose from those.
- The same reading names recur across faults of a module, so you can compare records.

### Network faults

On a motorcycle report, a fault whose `area` begins with `CAN bus` is one module reporting that another module's
messages are missing or wrong; the sender is named after the dot (`CAN bus · Sensor box`). The reporting module is the witness, not the
culprit. When several modules report timeouts from the same sender, look at that sender. If it is a module in the
report, check its own faults. If it isn't (the sensor box, for one), the listeners' faults are all the
report has on it, and the things to check are its connector, its power supply and its wiring. When many modules
report timeouts from many senders at the same mileage, suspect something common: battery voltage, a connector, the
bus wiring. `"CAN bus"` without a sender means the app doesn't know which message the fault is about.

On a car report there is no `area`; network faults say it in their description: a message that is missing, has
timed out or is invalid, often naming the message and its sender. The same reasoning applies: the module reporting it
is the witness, and many such faults at one mileage point to something common (battery voltage, the gateway, a bus).

Functions that depend on the missing data then switch off and store their own faults (`… deactivated due to external
signal fault`, `Limited operation: CAN bus input signal(s) faulty`). Group these with their cause instead of
counting them as separate problems.

### FSC entitlements

Some software features are sold separately and switched on by an enabling code (German *Freischaltcode*, FSC): a
signed certificate, tied to the VIN, stored in the module that provides the feature. On a motorcycle, examples are the
gearshift assistant, riding modes and Dynamic Traction Control, kept by the engine. On a car they are mostly in the
head unit: navigation, map updates (a map's upgrade level counts the updates), Apple CarPlay, BMW Apps, voice control;
some engine, steering and driver-assistance modules can hold them too.

`fscEntitlements` lists the certificates in force in that module: `swid` is the feature's software ID, `name` is
BMW's name for it (left out when the app doesn't know it), `detail` is the certificate's type and upgrade level,
which is bookkeeping you can ignore. The names are BMW's internal ones and don't always match the sales name of an
option, so don't pair an entitlement with an option code unless the names plainly agree. `"FSC entitlements": "None active"` under `values` means the module supports
enabling codes and has none in force. A module with neither doesn't use them, or (cars) is of a kind the app doesn't
ask: the car app reads them only from the modules that can carry them.

This is useful for checking what a vehicle really has. It is not the whole equipment list: most equipment is in
`options`.

### Options

`options` is the vehicle order (German *Fahrzeugauftrag*): the list of factory options and officially retrofitted
equipment as BMW option codes, stored in the vehicle. It is what the factory built plus what a dealer registered
later. Equipment fitted without registering it isn't in it.

Motorrad codes are three characters (`"224"`). Car codes are three characters too (`"2VB"`, `"609"`); four-character
codes on either are BMW's E-words and HO-words, which describe the build rather than equipment.

The vehicle order is stored in more than one module. `listedBy` appears on an option that only some of those copies
have: `"Instrument cluster only"`, `"Engine and ABS only"`, `"DME only"`. That can mean a module was replaced, or a
retrofit was written to one module and not the others. Worth a mention, not an alarm. On a car, the central gateway
keeps the master copy.

### Software versions

Cars only, so far: each module's `software` lists the program parts it runs, as BMW numbers them.

- Parts and versions are what BMW's programming system writes. A module's part numbers and versions are expected to
  match the car's `Software level`; the report doesn't include BMW's tables of which versions belong to which level,
  so it can't say whether a module is up to date. Don't call a version outdated from the file alone.
- Useful for a technician or a parts search: the exact software a module runs, and whether two reports of the same car
  differ (a module reprogrammed or replaced in between).
- A module without `software` didn't report its software list when the car was scanned.

### VIN copies

Motorrad. Each module stores the VIN of the vehicle it belongs to. A module `VIN` with `flag: "Differs"` (and the note `"VIN
mismatch"`) holds a different VIN: it came from another vehicle, or was replaced and never set up for this one. This
matters to a buyer and can explain odd behavior, but it isn't proof of anything improper: used modules are a normal
repair. Name the module and both VINs and leave the conclusion open.

### Odometer copies

Motorrad. The instrument cluster keeps the odometer (`Odometer`). Several other modules keep the mileage they last received
(`Odometer stored`). Small differences are normal: a module's copy can lag behind. A module whose stored mileage
is clearly **higher** than the cluster's odometer deserves a mention, and so does a fault recorded at a mileage
clearly above the odometer: a replaced cluster and a changed odometer are among the explanations. The report alone
can't settle which.

### Service data

Motorrad. `Next service in` (distance) and `Next service due` (date) are the countdown to the next scheduled service. More than
one module keeps a copy, and the copies can differ: a service reset doesn't always reach every module. The instrument
cluster's copy (or the central computer's, on the newest models) is normally the one shown on the dash. The report
can't tell you which copy is right when they differ: give the dash copy and note the difference. It has no record of
services done, only this countdown.

### Usage statistics

Motorrad. Values marked `"usageStatistic": true` say how the vehicle has been ridden: the engine's over-rev record and the ABS
module's time at steep lean angles.

- They come from one module's memory. A replaced or reprogrammed module starts over, so the values **may not cover the
  vehicle's whole life**. They are also totals over every rider the vehicle has had.
- Counters stop at their maximum.
- They may be missing because the person chose to leave them out when exporting, because the model doesn't keep
  them, or because the app can't read them on that software version. Absence tells you nothing.
- They describe a person's riding. Report them factually when asked and don't moralize or speculate past them. An
  over-rev count of 2 is two events, not a riding style.

## App specifics

- **Demo mode.** `app` ending in `(demo)` is the app's simulated vehicle (see [Six things](#six-things-to-get-right)).
- **Snapshot records depend on the app license (Motorrad).** Snapshot data is a licensed feature of the Motorrad app. A
  report made without it has no `snapshots` on any fault, though the modules may hold some. If no fault in the file has
  `snapshots`, don't conclude the modules stored none; the person can see in the app whether records exist. A car
  report has every record the app can decode.
- **Readings the app can't decode are left out** of a snapshot record, so a record can be shorter than what the
  module stored.
- **Usage statistics are the exporter's choice (Motorrad).** The export sheet has an "Include usage statistics" switch.
  Switched off, the values and their note are simply absent. Car reports have none.
- **Only faults are listed.** Checks that failed at some point since the memory was last cleared without becoming a
  stored fault are shown in the app but are not in the report.
- **Not in the report at all:** live sensor values, coding and settings, and service history; on a motorcycle, module
  software versions; on a car, the mileage, module VINs and the service countdown.
- **Descriptions are the app's own wording.** They can differ from the text in BMW's workshop software for the same
  code.
- **No guarantee.** The values are what the modules reported, as the app interprets them. The app's publisher doesn't
  guarantee they are complete or accurate.

## Analyzing a report

A way through that works:

1. **Check what you have.** `app` (demo?), `readAt` (how old?), `summary.modulesNotRead`, whether faults have
   `snapshots`, which unit system.
2. **Find the causes, not the count.** Sixteen faults are rarely sixteen problems. Group faults that share a mileage,
   a sender (`area` after `CAN bus ·`), or a component. Network timeouts and "deactivated" faults hang off whatever
   they depend on.
3. **Rank by what is real now.** Active before stored; recurring before one-off; recent mileage before old. Use
   `Fault class` and `Warning light` where present.
4. **Read the snapshots.** Standing or moving, engine running or not, battery voltage, temperatures. Say what the
   circumstances suggest.
5. **Then the rest**: module VINs, odometer copies, service countdown, software, and options and entitlements against
   what the person believes the vehicle has.
6. **Say what you can't tell.** The report can't show mechanical condition, wear, crash damage, or anything a module
   doesn't monitor. A fault names a circuit or a signal, and the cause can be the component, its connector, the wiring
   or the module.

And some cautions:

- Quote faults with module, code and the description as given, so the person can find them in the app and a
  technician can look them up.
- Don't suggest clearing the fault memory as a fix. Clearing is reasonable after a repair, to see what comes back.
- For faults in brakes, ABS or DSC, steering, airbags and belt tensioners, steering lock, throttle or anything else
  safety-related, recommend having the vehicle checked before it is ridden or driven, and say that the report is not a
  substitute for an inspection by a qualified technician.
- A stored fall-detection or tip-over fault means the module registered the vehicle on its side at that mileage. That
  includes dropping it in the garage. Report it; don't call it a crash.
- The VIN identifies the vehicle and, through registries, possibly its owner. Use it for the task at hand and don't
  repeat it where it isn't needed.
- If the report is of the demo vehicle, say so before anything else.
- You have no list of which options need which module or entitlement. Compare `options` and `fscEntitlements` with
  what the person tells you the vehicle has, not with each other.

## Versions

`schema` names the layout: `vae-diagwerk-health-report/` and a number.

- New keys, new `values` labels and new `details` names can appear **without** the number changing. Ignore a key you
  don't know.
- The number goes up when a key is removed or changes its meaning. This guide then describes each version.
- The wording of labels and descriptions can change between app versions (`app` tells you which made the file). Match
  on the labels in this guide, and fall back to reading the text.

A JSON Schema for version 1 is in [`schema/health-report-1.schema.json`](schema/health-report-1.schema.json), and
complete examples (each app's demo vehicle) in [`examples/demo-report.json`](examples/demo-report.json) (Motorrad) and
[`examples/demo-car-report.json`](examples/demo-car-report.json) (cars).

---

BMW, BMW Motorrad, MINI and all vehicle and module names are trademarks of BMW AG; Rolls-Royce is a trademark of
Rolls-Royce plc. Vandelay Auto Electronics LLC is not affiliated with or endorsed by BMW.
