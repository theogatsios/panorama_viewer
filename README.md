# Panorama Viewer (Qt6)

A QGIS plugin for viewing 360° panoramic photos (photospheres) directly in QGIS, with a live direction sector on the map. Works on **QGIS 3.x (Qt5)** and **QGIS 4.x (Qt6)**. Built on [Pannellum](https://pannellum.org/) and [Three.js](https://threejs.org/).

This is a QGIS 4 / Qt6 port of [Panorama Viewer](https://github.com/pavelpereverzev/panorama_viewer) by Pavel Pereverzev.

## Features

- View 360° photos from local files or web URLs stored in a layer's attributes
- Draw a direction sector on the map that follows the view in real time
- Set the initial view angle from a layer field
- Choose between three viewers: Pannellum, Three.js, or Canvas, which needs no WebGL or GPU
- Expanded view and "open in browser" buttons on the viewer

## Requirements

On QGIS 3.x with Qt5 the plugin uses QtWebKit and works out of the box.

On QGIS 4.x (Qt6) it uses QtWebEngine, which needs the Qt WebEngine Python bindings. These are included in some installers and are a separate package in others (for example `python3-pyqt6.qtwebengine` on Debian/Ubuntu). Without them the plugin still works, but panoramas open in your system web browser instead of inside QGIS.

## Quick guide

1. Open a layer of any geometry type.
2. Add a text field and fill it with direct links to 360° photos (local paths or web URLs).
3. Open the plugin and select the **Layer** and **Field** with the image links.
4. Select a feature on the map and click **View panorama**.

**Auto-update view** loads the panorama on every selection. **Show directions** draws the view sector on the map (the project CRS must be projected, not geographic). **Angles field** sets each panorama's initial heading. Hovering the bottom-right corner of the viewer shows buttons to open the panorama in your browser or to hide the controls and maximise the viewer.

## Troubleshooting

### "Embedded viewer not available"

On QGIS 4 (Qt6) the in-QGIS viewer needs the Qt WebEngine Python bindings. When they are missing, the plugin panel detects your system and shows the command to install them, with a **Copy** button and a **Check again** button. Panoramas open in your web browser until then.

| System | Command |
| --- | --- |
| Debian / Ubuntu / Mint | `sudo apt install python3-pyqt6.qtwebengine` |
| Fedora | `sudo dnf install python3-pyqt6-webengine` |
| Arch / Manjaro | `sudo pacman -S python-pyqt6-webengine` |
| openSUSE | find the name with `zypper search -s WebEngine \| grep -i pyqt` |
| Windows (OSGeo4W) | OSGeo4W Network Installer → Advanced Install → search "webengine" |
| Flatpak | not possible inside the Flatpak; install QGIS from your distribution or qgis.org |

Restart QGIS after installing.

Don't install `PyQt6-WebEngine` with **pip** into a system QGIS. The pip wheel bundles its own Qt, which won't match the Qt QGIS is built with and usually crashes QGIS.

### "Your browser does not have the necessary WebGL support"

Pannellum and Three.js need WebGL. Some QGIS builds start their embedded browser with the GPU switched off (`--disable-gpu`), so WebGL is unavailable whatever flags you set. You can confirm this by opening `chrome://gpu` in a QWebEngineView from the QGIS Python console.

The plugin detects this on the first panorama and switches to the **Canvas (no WebGL)** viewer, which draws the panorama on a plain 2D canvas. You can also pick it manually in the Viewer list. For the smoothest view, the message bar offers to open the panorama in your web browser.

Where QGIS allows it, the plugin also starts the embedded browser with `--ignore-gpu-blocklist --enable-unsafe-swiftshader`, which re-enables WebGL when the GPU driver is only blocklisted. Set `PANORAMA_VIEWER_NO_GPU_FLAGS=1` to turn this off.

## Building the plugin zip

```bash
git archive --prefix=panorama_viewer_qt6/ -o panorama_viewer_qt6.zip HEAD
```

Install it in QGIS via **Plugins → Manage and Install Plugins → Install from ZIP**.

## Credits and license

Original plugin © 2023 Pavel Pereverzev. QGIS 4 / Qt6 port © 2026 Theo Gatsios.

Licensed under the GNU General Public License v3.0 or later, see [LICENSE](LICENSE). Bundled libraries (Pannellum, three.js) are MIT-licensed, see [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).
