# Aeroponics IoT control — historical R&D snapshot

Python and MQTT integration work from a personal aeroponics lab. This archival portfolio snapshot shows device-control components, not a complete Home Assistant installation.

Related work: [sensor firmware](https://github.com/pilprod/aeroponics-sensor-firmware) · [project context, LinkedIn associations and photographs](https://papou.work/portfolio.html#home).

## Included work

- `hisense.py`: MQTT state tracking and IR commands for power, mode, temperature, fan, swing and display settings.
- `timberk.py`: humidifier state transitions, last-command tracking, and steam, ion, light and night-mode control.
- `timberk_propagator.py`: the original separate propagator-controller variant.
- `examples/`: sanitized Mosquitto and Zigbee2MQTT integration examples derived from the lab manifests.

The controllers use Python, `paho-mqtt`, JSON, command-line arguments, state subscriptions, timeouts and lock files. Home Assistant provided the user-facing control and monitoring layer; live installation data is excluded.

## Lab gallery

Photos from the original personal R&D installation. They show the wider hardware and Home Assistant environment; this repository contains only the controller and integration snapshot described above.

Five installation and workbench photographs have AI-retouched backgrounds or identifying areas for privacy and presentation.

### Monitoring and control

<p><img src="docs/images/home-assistant-dashboard.jpg" alt="Home Assistant dashboard displaying climate and water-system measurements, lighting controls and device states" width="900"></p>

**Home Assistant dashboard** — the interface for climate, lighting and water-system monitoring and control.

### Installation and assembly

<table>
  <tr>
    <td width="50%"><img src="docs/images/lighting-ventilation.jpg" alt="Suspended lighting, ventilation equipment and wiring inside the experimental enclosure" width="420"></td>
    <td width="50%"><img src="docs/images/water-system.jpg" alt="Water-system assembly with reservoirs, pumps, valves, tubing and wiring" width="420"></td>
  </tr>
  <tr>
    <td><strong>Lighting &amp; ventilation</strong><br>Enclosure, suspended fixtures and wiring.</td>
    <td><strong>Water system</strong><br>Reservoirs, pumps, valves and circulation plumbing.</td>
  </tr>
  <tr>
    <td width="50%"><img src="docs/images/enclosure-camera.jpg" alt="Camera and equipment mounted in the experimental enclosure" width="420"></td>
    <td width="50%"><img src="docs/images/power-shield.jpg" alt="Commercial power shield board integrated into the prototype" width="420"></td>
  </tr>
  <tr>
    <td><strong>Enclosure camera</strong><br>Camera placement within the installation.</td>
    <td><strong>Power shield</strong><br>A commercial board integrated into the electronics assembly.</td>
  </tr>
</table>

### Wiring and prototypes

<p><img src="docs/images/electronics-workbench.jpg" alt="Electronics workbench with development boards, sensors, wiring and soldering tools" width="900"></p>

**Electronics workbench** — component wiring and soldering during sensor and controller prototyping.

<p><img src="docs/images/wiring-diagram.jpg" alt="Original wiring diagram showing connections between system components" width="900"></p>

**Wiring diagram** — component connections documented during system design.

<p><a href="docs/images/breadboard-prototype.jpg"><img src="docs/images/breadboard-prototype.jpg" alt="Breadboard prototype with connected electronic components and jumper wires" width="480"></a></p>

**Breadboard prototype** — component connections and jumper wiring during controller prototyping. Click the photo to open the full 480 × 360 image.

### Root-zone observations

<p><img src="docs/images/root-chamber.jpg" alt="Root chamber with visible roots and tubing during the experiments" width="420"></p>

**Root chamber** — roots, chamber and tubing in the experimental installation.

## Configuration

Broker, credentials, topics and state/log paths are environment-configured. `.env.example` lists shared settings; export them explicitly because the scripts do not load dotenv files.

Override `MQTT_TOPIC_*` variables to map the generic `portfolio/<controller>/<setting>` namespace to reviewed devices. `MQTT_TOPIC_IR_SEND` requires a compatible IR transmitter. Runtime-path variables use controller prefixes, such as `HISENSE_LOCKFILE`, `TIMBERK_LOG_FILE` and `TIMBERK_LAST_IR_CODE_FILE`.

## Scope and safety

Python syntax has been parsed, but this snapshot has not been executed, integration-tested or safety-tested. Dependency versions were not locked, so current `paho-mqtt` compatibility remains unverified.

Examples are localhost-only lab configurations. Review authentication, transport security, IR-device compatibility and physical safety limits before connecting equipment; do not expose the examples publicly.

## Provenance

See [SOURCE.md](SOURCE.md) for original commits and snapshot changes. Original repositories remain intact. Upstream assets and runtime data are not bundled; no new license grant is added.
