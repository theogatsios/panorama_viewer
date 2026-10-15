# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Panorama Viewer NG - live channel for the external browser window
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

A browser tab opened on index_live.html stays connected to the plugin's
local web server:

  plugin -> browser   GET  /live/events   Server-Sent Events ("load this
                                          viewer page", "rotate to angle")
  browser -> plugin   POST /live/view     view changes (yaw / pitch / zoom)
                                          so the map's direction sector follows

Only the most recent command matters, so the hub keeps just that one plus a
version counter; a (re)connecting tab immediately gets the current panorama.
"""

import json
import threading

from qgis.PyQt.QtCore import QObject, pyqtSignal


class LiveHub:
    """Thread-safe 'latest command' store shared by all browser tabs."""

    KEEPALIVE = 15  # seconds between keep-alive comments on idle streams

    def __init__(self):
        self._cond = threading.Condition()
        self._version = 0
        self._message = None
        self._clients = 0
        self._closed = False

    @property
    def clients(self):
        with self._cond:
            return self._clients

    def publish(self, message):
        """Send a command (dict) to every connected tab."""
        with self._cond:
            self._version += 1
            self._message = json.dumps(message)
            self._cond.notify_all()

    def close(self):
        with self._cond:
            self._closed = True
            self._cond.notify_all()

    def stream(self, write):
        """Run one SSE connection until the client leaves or the hub closes.
        `write(bytes)` raises OSError when the browser tab is gone."""
        with self._cond:
            self._clients += 1
            seen = 0
        try:
            while True:
                with self._cond:
                    if self._version == seen and not self._closed:
                        self._cond.wait(self.KEEPALIVE)
                    if self._closed:
                        return
                    version, message = self._version, self._message
                if version != seen and message is not None:
                    seen = version
                    write("data: {}\n\n".format(message).encode("utf-8"))
                else:
                    write(b": keep-alive\n\n")
        except OSError:
            return
        finally:
            with self._cond:
                self._clients -= 1


class LiveBridge(QObject):
    """Carries view updates from the server thread into QGIS' main thread.
    Connect `view_changed` to a method of a QObject living in the main thread
    so Qt queues the call across threads."""

    view_changed = pyqtSignal(str)


def handle_live_request(handler, hub, bridge):
    """Route /live/* requests. Returns True when the request was handled."""
    path = handler.path.split("?", 1)[0]

    if handler.command == "GET" and path == "/live/events":
        handler.send_response(200)
        handler.send_header("Content-Type", "text/event-stream")
        handler.send_header("Connection", "keep-alive")
        handler.end_headers()

        def write(data):
            handler.wfile.write(data)
            handler.wfile.flush()

        hub.stream(write)
        handler.close_connection = True
        return True

    if handler.command == "POST" and path == "/live/view":
        length = int(handler.headers.get("Content-Length") or 0)
        body = handler.rfile.read(min(length, 4096)).decode("utf-8", "replace")
        handler.send_response(204)
        handler.end_headers()
        if body.startswith("{"):
            bridge.view_changed.emit(body)
        return True

    return False
