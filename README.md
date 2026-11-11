# Diagwerk health report format

**VAE Diagwerk for Motorrad** reads BMW Motorrad motorcycles and scooters through the diagnostic port. Its health
report (every control module's fault memory, with snapshot data, service data, option codes and more) can be exported
as a PDF to read or as **JSON to hand to an AI assistant**.

This repository describes that JSON file, so an assistant that has never seen one can read it correctly.

| | |
| --- | --- |
| [GUIDE.md](GUIDE.md) | **Start here.** What the file is, every key, and the BMW and app background needed to interpret it. Written for an AI assistant; fine for people too. |
| [schema/health-report-1.schema.json](schema/health-report-1.schema.json) | JSON Schema for `vae-diagwerk-health-report/1`. |
| [examples/demo-report.json](examples/demo-report.json) | A complete report, exported from the app's demo mode. |

## Using a report with an assistant

In the app: **Health report › Export › JSON**. Give the file to your assistant and ask your question. The file links
to the guide; if your assistant can't open links, paste [GUIDE.md](GUIDE.md) into the conversation along with the file.

The export sheet's **Include usage statistics** switch decides whether the over-rev record and time at steep lean
angles go into the file. The file also contains the vehicle's VIN. Share it as you would the vehicle's registration
papers.

## The example

`examples/demo-report.json` is the app's simulated motorcycle, not a real vehicle. It is there to show the layout with
a bit of everything: active and stored faults, snapshot records, a module that could not be read, usage statistics,
enabling codes and options. Its values are not a consistent history (some faults are recorded at a higher mileage than
the odometer), so don't use it to test an assistant's conclusions, only its reading of the format. It was exported
with imperial units; a report in metric looks the same with km, °C and bar.

## Versions

The file names its layout in `schema`. Keys can be added without the version changing; a reader should ignore keys it
doesn't know. The number goes up when a key is removed or changes its meaning, and this repository will then describe
each version.

## About

The app's terms and privacy policy: [vandelayauto.net/diagwerk/terms](https://vandelayauto.net/diagwerk/terms/),
[vandelayauto.net/diagwerk/privacy](https://vandelayauto.net/diagwerk/privacy/). Questions:
[support@vandelayauto.net](mailto:support@vandelayauto.net).

Reports are provided as is: they show what the vehicle's control modules reported, as interpreted by VAE's own
analysis, without any guarantee that they are complete or accurate, and are not a substitute for an inspection by a
qualified technician.

BMW, BMW Motorrad and all vehicle and module names are trademarks of BMW AG. Vandelay Auto Electronics LLC is not
affiliated with or endorsed by BMW.
