def classFactory(iface):
    from .plugin import TesselaPlugin
    return TesselaPlugin(iface)
