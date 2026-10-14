# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Panorama Viewer NG - help panel for missing Qt WebEngine
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

import os
import sys
import importlib

from qgis.PyQt.QtCore import Qt, QUrl, QTimer
from qgis.PyQt.QtGui import QDesktopServices, QFontDatabase
from qgis.PyQt.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QHBoxLayout,
    QSizePolicy,
    QFrame,
    QScrollArea,
)

from .compat import QT6

TROUBLESHOOTING_URL = "https://github.com/theogatsios/panorama_viewer#troubleshooting"


class Fix:
    """What to tell the user for a detected environment."""

    def __init__(self, platform, command=None, steps=None, search=None):
        self.platform = platform   # human-readable, e.g. "Ubuntu 24.04"
        self.command = command     # one-line install command, if there is one
        self.steps = steps         # text instructions when there is no command
        self.search = search       # command to find the package if the name differs


def _os_release():
    data = {}
    for path in ("/etc/os-release", "/usr/lib/os-release"):
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    if "=" in line:
                        k, v = line.rstrip("\n").split("=", 1)
                        data[k] = v.strip().strip('"')
            break
        except OSError:
            continue
    return data


def detect_fix():
    """Work out how QGIS is installed and how to add Qt WebEngine to it."""
    pyqt = "PyQt6" if QT6 else "PyQt5"

    # --- Flatpak: system packages are invisible inside the sandbox
    if os.path.exists("/.flatpak-info") or os.environ.get("FLATPAK_ID"):
        return Fix(
            "QGIS Flatpak",
            steps=(
                "The Flatpak build of QGIS does not include Qt WebEngine, and system "
                "packages cannot be added to it. To use the embedded viewer, install QGIS "
                "from your distribution or the qgis.org repository instead. "
                "Until then, panoramas open in your web browser."
            ),
        )

    # --- conda / mamba environments
    if os.path.isdir(os.path.join(sys.prefix, "conda-meta")):
        env = os.environ.get("CONDA_DEFAULT_ENV", "")
        env_flag = " -n {}".format(env) if env and env != "base" else ""
        return Fix(
            "conda environment" + (" '{}'".format(env) if env else ""),
            search="conda search -c conda-forge \"*webengine*\"",
            steps=(
                "Install the {} WebEngine package from conda-forge into the environment "
                "QGIS runs in{}, then restart QGIS. Use the search command below to find "
                "the exact package name for your Qt version."
            ).format(pyqt, " (conda install{} -c conda-forge <package>)".format(env_flag)),
        )

    # --- Linux distributions
    if sys.platform.startswith("linux"):
        rel = _os_release()
        name = rel.get("PRETTY_NAME") or rel.get("NAME") or "Linux"
        ids = {rel.get("ID", "")} | set(rel.get("ID_LIKE", "").split())

        if ids & {"debian", "ubuntu"}:
            pkg = "python3-pyqt6.qtwebengine" if QT6 else "python3-pyqt5.qtwebengine"
            return Fix(name, command="sudo apt install " + pkg,
                       search="apt search pyqt 2>/dev/null | grep -i webengine")
        if ids & {"fedora", "rhel", "centos"}:
            pkg = "python3-pyqt6-webengine" if QT6 else "python3-qt5-webengine"
            return Fix(name, command="sudo dnf install " + pkg,
                       search="dnf search webengine | grep -i pyqt")
        if ids & {"arch"}:
            pkg = "python-pyqt6-webengine" if QT6 else "python-pyqtwebengine"
            return Fix(name, command="sudo pacman -S " + pkg,
                       search="pacman -Ss webengine | grep -i pyqt")
        if ids & {"suse", "opensuse", "opensuse-leap", "opensuse-tumbleweed"}:
            return Fix(name, search="zypper search -s WebEngine | grep -i pyqt",
                       steps="Install the {} WebEngine package with zypper, then restart QGIS. "
                             "Use the search command below to find its exact name.".format(pyqt))
        return Fix(name, steps=(
            "Install your distribution's {} WebEngine package (often named like "
            "python3-pyqt6-webengine), then restart QGIS.").format(pyqt))

    # --- Windows
    if sys.platform == "win32":
        osgeo = os.environ.get("OSGEO4W_ROOT") or (
            sys.prefix if "osgeo4w" in sys.prefix.lower() else "")
        if osgeo:
            return Fix("Windows (OSGeo4W)", steps=(
                "Close QGIS, run the OSGeo4W Network Installer, choose "
                "\"Advanced Install\", search for \"webengine\" and install the "
                "{} WebEngine package that matches your QGIS. Then start QGIS again."
            ).format(pyqt))
        return Fix("Windows", steps=(
            "This QGIS installer does not include Qt WebEngine. Install QGIS with the "
            "OSGeo4W Network Installer and add the {} WebEngine package, or keep using "
            "browser mode."
        ).format(pyqt))

    # --- macOS and anything else
    if sys.platform == "darwin":
        return Fix("macOS", steps=(
            "This QGIS build does not include Qt WebEngine. Panoramas open in your "
            "web browser; check the troubleshooting page for macOS options."))

    return Fix(sys.platform, steps="Install the {} WebEngine Python bindings for the Python "
                                   "that QGIS uses, then restart QGIS.".format(pyqt))


def webengine_importable():
    """Re-check (e.g. after the user installed the package) without restarting."""
    importlib.invalidate_caches()
    mod = "PyQt6.QtWebEngineWidgets" if QT6 else "PyQt5.QtWebEngineWidgets"
    try:
        importlib.import_module(mod)
        return True, ""
    except Exception as e:
        return False, str(e)


def _command_row(text):
    """Read-only monospace field plus a Copy button."""
    row = QHBoxLayout()
    field = QLineEdit(text)
    field.setReadOnly(True)
    field.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
    field.setCursorPosition(0)
    btn = QPushButton("Copy")
    btn.setToolTip("Copy command to clipboard")

    def copy():
        QApplication.clipboard().setText(text)
        btn.setText("Copied ✓")
        QTimer.singleShot(1500, lambda: btn.setText("Copy"))

    btn.clicked.connect(copy)
    row.addWidget(field, 1)
    row.addWidget(btn)
    return row


class NoWebEngineWidget(QWidget):
    """Shown in place of the embedded viewer when Qt WebEngine is missing."""

    def __init__(self, error_text=None, parent=None):
        super().__init__(parent)
        self.fix = detect_fix()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        outer = QVBoxLayout(inner)
        outer.addStretch(1)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

        box = QWidget()
        box.setMaximumWidth(560)
        lay = QVBoxLayout(box)
        lay.setSpacing(8)

        title = QLabel("<b>Embedded viewer not available</b>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)

        intro = QLabel(
            "Panoramas will open in your web browser for now. The in-QGIS viewer "
            "needs the Qt WebEngine Python bindings, which this QGIS installation "
            "doesn't have."
        )
        intro.setWordWrap(True)
        intro.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(intro)

        detected = QLabel("Detected: <b>{}</b>".format(self.fix.platform))
        detected.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(detected)

        if self.fix.command:
            lay.addWidget(QLabel("Run this in a terminal, then restart QGIS:"))
            lay.addLayout(_command_row(self.fix.command))
        if self.fix.steps:
            steps = QLabel(self.fix.steps)
            steps.setWordWrap(True)
            lay.addWidget(steps)
        if self.fix.search and not self.fix.command:
            lay.addWidget(QLabel("Find the package with:"))
            lay.addLayout(_command_row(self.fix.search))

        # action buttons
        buttons = QHBoxLayout()
        self.btn_check = QPushButton("Check again")
        self.btn_check.setToolTip("Check whether Qt WebEngine is now installed")
        self.btn_check.clicked.connect(self.check_again)
        btn_help = QPushButton("Troubleshooting…")
        btn_help.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(TROUBLESHOOTING_URL)))
        buttons.addStretch(1)
        if self.fix.platform != "QGIS Flatpak":  # nothing to re-check inside a Flatpak
            buttons.addWidget(self.btn_check)
        buttons.addWidget(btn_help)
        buttons.addStretch(1)
        lay.addLayout(buttons)

        self.status = QLabel("")
        self.status.setWordWrap(True)
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.hide()
        lay.addWidget(self.status)

        # technical details, collapsed by default
        if error_text or (self.fix.search and self.fix.command):
            self.btn_details = QToolButton()
            self.btn_details.setText("Technical details")
            self.btn_details.setCheckable(True)
            self.btn_details.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            self.btn_details.setArrowType(Qt.ArrowType.RightArrow)
            self.btn_details.setAutoRaise(True)
            self.details = QWidget()
            dl = QVBoxLayout(self.details)
            dl.setContentsMargins(0, 0, 0, 0)
            if self.fix.search and self.fix.command:
                dl.addWidget(QLabel("Package not found? Look up its name with:"))
                dl.addLayout(_command_row(self.fix.search))
            if error_text:
                err = QLabel(error_text)
                err.setWordWrap(True)
                err.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                err.setFrameShape(QFrame.Shape.StyledPanel)
                err.setStyleSheet("color: gray; padding: 4px;")
                dl.addWidget(err)
            self.details.hide()

            def toggle(on):
                self.details.setVisible(on)
                self.btn_details.setArrowType(
                    Qt.ArrowType.DownArrow if on else Qt.ArrowType.RightArrow)

            self.btn_details.toggled.connect(toggle)
            lay.addWidget(self.btn_details, 0, Qt.AlignmentFlag.AlignHCenter)
            lay.addWidget(self.details)

        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(box, 10)
        row.addStretch(1)
        outer.addLayout(row)
        outer.addStretch(1)
        scroll.setWidget(inner)

    def check_again(self):
        ok, err = webengine_importable()
        self.status.show()
        if ok:
            self.status.setText(
                "<b>Qt WebEngine is installed.</b> Restart QGIS to use the embedded viewer.")
        else:
            self.status.setText("Still not found. After installing, restart QGIS "
                                "if the package doesn't show up here.")
