# Source provenance

This public-facing snapshot selects historical personal R&D files from private GitLab repositories owned by the project author. Source links may require access. The original repositories and their history are not migrated or deleted.

| Source repository | Snapshot commit | Selected source paths |
| --- | --- | --- |
| https://gitlab.com/leafcoin/legacy/home-assistant.git | `08df82f97fd10b830d6bc90f2175aa084ca02156` | `data/scripts/hisense.py`, `data/scripts/timberk.py`, `data/scripts/timberk_propagator.py` |
| https://gitlab.com/leafcoin/legacy/mosquitto.git | `32cda175eb4641ebd24184dbbc2bfaaf8e24afef` | `docker-compose.yaml`, adapted as an example |
| https://gitlab.com/leafcoin/legacy/zigbee2mqtt.git | `989cdee463ba3b74994175e7b58e686feb62233e` | `docker-compose.yaml`, adapted as an example; configuration reduced to generic integration fields |

The archived commits identify Ilya Popov (Ilya Papou) as their author. Third-party scaffolds and assets were excluded from this snapshot.

## Changes made for this snapshot

- Copied the three current Python controller files, preserving their control flow and command payloads. Replaced broker, authentication, MQTT-topic and runtime-path constants with environment-backed configuration and generic defaults.
- Replaced local installation directories and hardware mappings in example manifests with relative directories and configurable generic device paths. Local service ports bind to loopback. These examples are documentation aids, not validated deployments.
- Added a minimal, newly written Zigbee2MQTT configuration example with generic MQTT integration fields. It is not a copy of an installed device network.
- Added this provenance document, configuration example, ignore rules and explanatory README. No source history is copied into the public snapshot.

## Third-party software

The examples reference Eclipse Mosquitto and Zigbee2MQTT images. Python controllers import `paho-mqtt`. These upstream projects remain separate dependencies; their source code is not redistributed here. Manufacturer names identify devices used in the historical lab and do not imply employment, affiliation or endorsement.

No LICENSE file was present in the selected source repositories. This snapshot adds no license grant and makes no claim that omitted third-party assets can be relicensed.
