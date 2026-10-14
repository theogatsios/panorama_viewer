# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Panorama Viewer (Qt6) - compatibility layer
                                 A QGIS plugin
        copyright            : (C) 2026 by Theo Gatsios
        email                : theogat@protonmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 3 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

"""
Compatibility layer so the plugin runs on both
QGIS 3.x (Qt5 / PyQt5) and QGIS 4.x (Qt6 / PyQt6).

Web backend selection, in order of preference:
  1. "webkit"    - QtWebKit (QGIS 3.x Qt5 builds; what the plugin was built on)
  2. "webengine" - QtWebEngine (QGIS 4.x Qt6 builds, when PyQt6-WebEngine is installed)
  3. None        - no embedded browser available; panoramas open in the
                   system web browser instead
"""

from qgis.PyQt.QtCore import QT_VERSION_STR
from qgis.core import Qgis, QgsWkbTypes, QgsUnitTypes

QT6 = int(QT_VERSION_STR.split(".")[0]) >= 6

# ---------------------------------------------------------------- QAction
try:  # Qt6: QAction lives in QtGui
    from qgis.PyQt.QtGui import QAction  # noqa: F401
except ImportError:  # Qt5: QAction lives in QtWidgets
    from qgis.PyQt.QtWidgets import QAction  # noqa: F401

# ---------------------------------------------------------------- web backend
WEB_BACKEND = None
QWebView = QWebPage = QWebSettings = QWebInspector = None
QWebEngineView = QWebEnginePage = QWebEngineSettings = QWebEngineProfile = None

if not QT6:
    try:
        from qgis.PyQt.QtWebKitWidgets import QWebView, QWebPage, QWebInspector
        from qgis.PyQt.QtWebKit import QWebSettings
        WEB_BACKEND = "webkit"
    except Exception:
        WEB_BACKEND = None

WEB_BACKEND_ERROR = None  # why no embedded engine could be loaded


def _load_webengine():
    """Import QtWebEngine classes, trying QGIS' PyQt wrapper first and then
    PyQt6 / PyQt5 directly (some QGIS builds don't ship the wrapper module)."""
    errors = []
    for view_mod, core_mods in (
        ("qgis.PyQt.QtWebEngineWidgets", ("qgis.PyQt.QtWebEngineCore", "qgis.PyQt.QtWebEngineWidgets")),
        ("PyQt6.QtWebEngineWidgets", ("PyQt6.QtWebEngineCore",)),
        ("PyQt5.QtWebEngineWidgets", ("PyQt5.QtWebEngineWidgets",)),
    ):
        if QT6 and view_mod.startswith("PyQt5"):
            continue
        if not QT6 and view_mod.startswith("PyQt6"):
            continue
        try:
            import importlib
            vm = importlib.import_module(view_mod)
            view = vm.QWebEngineView
            for cm_name in core_mods:
                try:
                    cm = importlib.import_module(cm_name)
                    return view, cm.QWebEnginePage, cm.QWebEngineSettings, cm.QWebEngineProfile
                except (ImportError, AttributeError) as e:
                    errors.append("{}: {}".format(cm_name, e))
        except Exception as e:  # ImportError, or RuntimeError about init order
            errors.append("{}: {}".format(view_mod, e))
    raise ImportError("; ".join(errors))


if WEB_BACKEND is None:
    try:
        QWebEngineView, QWebEnginePage, QWebEngineSettings, QWebEngineProfile = _load_webengine()
        WEB_BACKEND = "webengine"
    except Exception as e:
        WEB_BACKEND = None
        WEB_BACKEND_ERROR = str(e)


# ---------------------------------------------------------------- QGIS enums
def _first_attr(candidates):
    for owner, path in candidates:
        obj = owner
        try:
            for part in path.split("."):
                obj = getattr(obj, part)
            return obj
        except AttributeError:
            continue
    return None


POLYGON_GEOMETRY = _first_attr([
    (Qgis, "GeometryType.Polygon"),          # QGIS >= 3.30 / 4.x
    (QgsWkbTypes, "PolygonGeometry"),        # older QGIS 3.x
])

DEGREES_UNIT = _first_attr([
    (Qgis, "DistanceUnit.Degrees"),          # QGIS >= 3.30 / 4.x
    (QgsUnitTypes, "DistanceUnit.Degrees"),
    (QgsUnitTypes, "DistanceDegrees"),       # older QGIS 3.x
])

MSG_INFO = _first_attr([
    (Qgis, "MessageLevel.Info"),
    (Qgis, "Info"),
])


def is_string_field(field):
    """True for text fields on both QVariant (QGIS 3) and QMetaType (QGIS 4)
    based field types. QVariant.String and QMetaType.QString are both 10."""
    t = field.type()
    t = getattr(t, "value", t)  # PyQt6 enums are not ints
    try:
        return int(t) == 10
    except (TypeError, ValueError):
        return False
