from qgis.PyQt.QtGui import QIcon

from .browse_dialog import BrowseDialog

import os

ICON_PATH = os.path.join(os.path.dirname(__file__), "icon.png")


class TesselaPlugin:
    """Uso público: mostra os temas publicados e leva para a compra no Gumroad/Payhip."""

    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dialog = None

    def initGui(self):
        try:
            from qgis.PyQt.QtGui import QAction
        except ImportError:
            from qgis.PyQt.QtWidgets import QAction

        self.action = QAction(QIcon(ICON_PATH), "Ver temas do Tessela", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addPluginToMenu("&Tessela", self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        self.iface.removePluginMenu("&Tessela", self.action)
        self.iface.removeToolBarIcon(self.action)

    def run(self):
        self.dialog = BrowseDialog(self.iface.mainWindow())
        self.dialog.show()
