# Third-Party Notices

Impulse bundles the following third-party components. Their licences are listed
below, and each project's own licence text applies to that component.

| Component | Licence |
|---|---|
| Whisper.cpp | MIT |
| GGML | MIT |
| faster-whisper | MIT |
| CTranslate2 | MIT |
| OpenAI Whisper models (`ggml-base.en`) | MIT |
| NumPy, Pillow, psutil, requests | BSD-3-Clause / MIT / HPND |
| pywebview | BSD-3-Clause |
| pystray | LGPL v3 |
| **PySide6 (Qt for Python)** | **LGPL v3** |

## Qt / PySide6 (LGPL v3)

Impulse uses PySide6, the official Python bindings for the Qt framework, for the
on-screen recording indicator. PySide6 and the Qt libraries it depends on are
licensed under the GNU Lesser General Public License version 3.

The full text of the LGPL v3 is available at
<https://www.gnu.org/licenses/lgpl-3.0.html>.

In accordance with the LGPL, the Qt libraries are distributed as separate
dynamic libraries inside the application's `_internal/PySide6` directory rather
than statically linked. You may replace them with your own compatible build of
Qt by substituting those files. The corresponding source for PySide6 and Qt is
available from <https://download.qt.io/official_releases/QtForPython/> and
<https://download.qt.io/official_releases/qt/>.

## pystray (LGPL v3)

Impulse uses pystray for its system tray icon, under the same terms described
above. Source: <https://github.com/moses-palmer/pystray>.
