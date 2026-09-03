import json
import os
import io
import zipfile
from datetime import datetime

from qgis.PyQt.QtCore import QUrl, Qt, QSize, QRectF, QPointF
from qgis.PyQt.QtGui import QPixmap, QDesktopServices, QPainter, QColor, QPainterPath, QPen
from qgis.PyQt.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from qgis.PyQt.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QPushButton,
    QLineEdit,
    QFrame,
    QSizePolicy,
    QGraphicsView,
    QGraphicsScene,
    QFileDialog,
    QMessageBox,
    QScrollArea,
)

# Se um dia você trocar de usuário ou repositório no GitHub, atualize aqui.
SHOP_OWNER = "pedromoreli95"
SHOP_REPO = "tessela-publico"

CATEGORIES = ["Infraestrutura", "Ambiental", "Socioespacial", "Socioeconômico"]

INK = "#17211C"
INK_SOFT = "#5C6B62"
CONTOUR = "#2F6B4F"
CONTOUR_DARK = "#234F3B"
BRASS = "#B8853A"
LINE = "#E5E4DF"
PAPER_DIM = "#F7F7F5"

STYLESHEET = f"""
QDialog {{
    background: #FFFFFF;
}}
QLabel {{
    color: {INK};
}}
QLabel#wordmark {{
    font-size: 19px;
    font-weight: 700;
}}
QLabel#tagline {{
    color: {INK_SOFT};
    font-size: 12px;
}}
QLineEdit {{
    border: 1px solid {LINE};
    border-radius: 7px;
    padding: 8px 10px;
    font-size: 12px;
    background: {PAPER_DIM};
    color: {INK};
}}
QLineEdit:focus {{
    border: 1px solid {CONTOUR};
    background: #FFFFFF;
}}
QPushButton#refreshBtn {{
    background: transparent;
    color: {INK_SOFT};
    border: 1px solid {LINE};
    border-radius: 7px;
    padding: 7px 14px;
    font-size: 12px;
    font-weight: 600;
}}
QPushButton#refreshBtn:hover {{
    color: {INK};
    border-color: {INK};
}}
QPushButton#filterChip {{
    background: {PAPER_DIM};
    color: {INK_SOFT};
    border: 1px solid {LINE};
    border-radius: 14px;
    padding: 5px 12px;
    font-size: 11px;
    font-weight: 600;
}}
QPushButton#filterChip:checked {{
    background: {CONTOUR};
    color: white;
    border-color: {CONTOUR};
}}
QPushButton#filterChip:hover {{
    border-color: {CONTOUR};
}}
QPushButton#buyBtn {{
    background: {CONTOUR};
    color: white;
    border: none;
    border-radius: 8px;
    padding: 9px;
    font-size: 13px;
    font-weight: 600;
}}
QPushButton#buyBtn:hover {{
    background: {CONTOUR_DARK};
}}
QPushButton#buyBtn:disabled {{
    background: {LINE};
    color: {INK_SOFT};
}}
QListWidget {{
    border: none;
    background: transparent;
    outline: none;
}}
QListWidget::item {{
    border-radius: 10px;
    margin-bottom: 4px;
}}
QListWidget::item:selected {{
    background: {PAPER_DIM};
}}
QListWidget::item:hover {{
    background: #FBFBFA;
}}
QFrame#previewCard {{
    background: {PAPER_DIM};
    border: 1px solid {LINE};
    border-radius: 12px;
}}
QGraphicsView#previewImage {{
    background: #FFFFFF;
    border: 1px solid {LINE};
    border-radius: 10px;
}}
QLabel#themeName {{
    font-size: 18px;
    font-weight: 700;
}}
QLabel#priceLabel {{
    color: {BRASS};
    font-size: 15px;
    font-weight: 700;
}}
QLabel#categoryTag {{
    color: {CONTOUR};
    font-size: 11px;
    font-weight: 600;
}}
QLabel#dateLabel {{
    color: {INK_SOFT};
    font-size: 11px;
}}
QLabel#layersSummary {{
    color: {INK};
    font-size: 12px;
    font-weight: 600;
    margin-top: 4px;
}}
QLabel#layerRowName {{
    color: {INK};
    font-size: 11px;
}}
QScrollArea#layersScroll {{
    border: none;
    background: transparent;
}}
QLabel#statusLabel {{
    color: {INK_SOFT};
    font-size: 11px;
}}
QLabel#cardName {{
    font-size: 13px;
    font-weight: 600;
}}
QLabel#cardPrice {{
    color: {BRASS};
    font-size: 12px;
    font-weight: 600;
}}
QLabel#cardPrice[free="true"] {{
    color: {CONTOUR};
}}
QLabel#hint {{
    color: {INK_SOFT};
    font-size: 11px;
}}
"""


def format_date(iso_date):
    if not iso_date:
        return ""
    try:
        return datetime.strptime(iso_date, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return ""


def make_color_bar_pixmap(colors, width, height=18, radius=6):
    """Desenha uma barrinha com as cores do estilo, uma faixa ao lado da outra."""
    pixmap = QPixmap(max(width, 1), height)
    pixmap.fill(Qt.GlobalColor.transparent)
    if not colors:
        return pixmap

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(0, 0, width, height, radius, radius)
    painter.setClipPath(path)

    n = len(colors)
    seg_w = width / n
    for i, hex_color in enumerate(colors):
        color = QColor(hex_color)
        if not color.isValid():
            continue
        painter.fillRect(QRectF(i * seg_w, 0, seg_w + 1, height), color)
    painter.end()
    return pixmap


def make_symbology_icon(size=14):
    """Ícone sutil: círculo verde sólido, representando simbologia configurada."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(CONTOUR))
    p.drawEllipse(QRectF(1, 1, size - 2, size - 2))
    p.end()
    return pm


def make_labels_icon(size=14):
    """Ícone sutil: quadrado dourado com um "T", representando rótulos configurados."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(BRASS))
    p.drawRoundedRect(QRectF(0, 0, size, size), 3, 3)
    pen = QPen(QColor("#FFFFFF"))
    pen.setWidthF(1.6)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.drawLine(QPointF(size * 0.28, size * 0.32), QPointF(size * 0.72, size * 0.32))
    p.drawLine(QPointF(size * 0.5, size * 0.32), QPointF(size * 0.5, size * 0.75))
    p.end()
    return pm


class ThemeCard(QWidget):
    """Uma linha da lista: miniatura + nome + preço."""

    def __init__(self, theme):
        super().__init__()
        self.theme = theme

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(50, 50)
        self.thumb_label.setStyleSheet(
            f"background: {PAPER_DIM}; border: 1px solid {LINE}; border-radius: 8px;"
        )
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.thumb_label)

        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        name_label = QLabel(theme["name"])
        name_label.setObjectName("cardName")
        name_label.setWordWrap(True)
        price_label = QLabel("Grátis" if theme.get("free") else theme.get("price", ""))
        price_label.setObjectName("cardPrice")
        if theme.get("free"):
            price_label.setProperty("free", "true")
        text_col.addWidget(name_label)
        text_col.addWidget(price_label)
        layout.addLayout(text_col, 1)

    def set_thumbnail(self, pixmap):
        self.thumb_label.setPixmap(
            pixmap.scaled(
                50, 50,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.thumb_label.setStyleSheet(f"border: 1px solid {LINE}; border-radius: 8px;")


class ZoomableImageView(QGraphicsView):
    """Visualizador de imagem com zoom (roda do mouse) e arraste (clicar e arrastar)."""

    def __init__(self):
        super().__init__()
        self.setObjectName("previewImage")
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._pixmap_item = None

        self.set_empty_message("Selecione um tema")

    def set_empty_message(self, text):
        self._scene.clear()
        self._pixmap_item = None
        text_item = self._scene.addText(text)
        text_item.setDefaultTextColor(Qt.GlobalColor.gray)

    def set_image(self, pixmap):
        self._scene.clear()
        self._pixmap_item = self._scene.addPixmap(pixmap)
        self._scene.setSceneRect(self._pixmap_item.boundingRect())
        self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatioByExpanding)

    def has_image(self):
        return self._pixmap_item is not None

    def wheelEvent(self, event):
        if self._pixmap_item is None:
            super().wheelEvent(event)
            return
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)

    def mouseDoubleClickEvent(self, event):
        if self._pixmap_item is not None:
            self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
        super().mouseDoubleClickEvent(event)


class BrowseDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Tessela")
        self.setMinimumSize(680, 420)
        self.resize(1250, 830)
        self.setStyleSheet(STYLESHEET)

        self.manager = QNetworkAccessManager(self)
        self.themes = []
        self.themes_by_id = {}
        self.current_theme = None
        self.thumb_replies = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(14)

        # ---------- cabeçalho ----------
        header_row = QHBoxLayout()
        header_row.setSpacing(10)

        logo_label = QLabel()
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        logo_pixmap = QPixmap(icon_path)
        if not logo_pixmap.isNull():
            logo_label.setPixmap(
                logo_pixmap.scaled(34, 34, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            )
        header_row.addWidget(logo_label)

        header_col = QVBoxLayout()
        header_col.setSpacing(2)
        wordmark = QLabel("Tessela")
        wordmark.setObjectName("wordmark")
        tagline = QLabel("Estilos prontos para o QGIS")
        tagline.setObjectName("tagline")
        header_col.addWidget(wordmark)
        header_col.addWidget(tagline)
        header_row.addLayout(header_col)
        header_row.addStretch()

        self.refresh_btn = QPushButton("Atualizar")
        self.refresh_btn.setObjectName("refreshBtn")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        header_row.addWidget(self.refresh_btn, 0, Qt.AlignmentFlag.AlignTop)
        outer.addLayout(header_row)

        # ---------- busca ----------
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Buscar por nome ou categoria")
        outer.addWidget(self.search_edit)

        # ---------- filtro por categoria ----------
        self.active_category = None
        filter_row = QHBoxLayout()
        filter_row.setSpacing(6)
        self.category_buttons = {}
        for label in ["Todos"] + CATEGORIES:
            btn = QPushButton(label)
            btn.setObjectName("filterChip")
            btn.setCheckable(True)
            btn.setChecked(label == "Todos")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, lbl=label: self.on_category_filter(lbl))
            filter_row.addWidget(btn)
            self.category_buttons[label] = btn
        filter_row.addStretch()
        outer.addLayout(filter_row)

        # ---------- corpo ----------
        body = QHBoxLayout()
        body.setSpacing(18)

        self.list_widget = QListWidget()
        self.list_widget.setFixedWidth(240)
        self.list_widget.setSpacing(2)
        body.addWidget(self.list_widget)

        self.preview_card = QFrame()
        self.preview_card.setObjectName("previewCard")

        preview_layout = QVBoxLayout(self.preview_card)
        preview_layout.setContentsMargins(20, 20, 20, 20)
        preview_layout.setSpacing(12)

        self.preview_view = ZoomableImageView()
        self.preview_view.setMinimumHeight(160)
        self.preview_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        preview_layout.addWidget(self.preview_view, 1)

        # Tudo que vem depois do mapa (dica, nome, preço, lista de camadas) mora
        # dentro de um único scroll — assim, se a janela ficar pequena, esse
        # bloco rola em vez de espremer e sobrepor o mapa.
        bottom_scroll = QScrollArea()
        bottom_scroll.setObjectName("layersScroll")
        bottom_scroll.setWidgetResizable(True)
        bottom_scroll.setFrameShape(QFrame.Shape.NoFrame)
        bottom_scroll.setMaximumHeight(340)
        bottom_scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        bottom_container = QWidget()
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(0, 0, 4, 0)
        bottom_layout.setSpacing(10)

        hint = QLabel("Role o mouse para dar zoom · arraste para mover · duplo clique para centralizar")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        bottom_layout.addWidget(hint)

        info_row = QHBoxLayout()
        name_price_col = QVBoxLayout()
        name_price_col.setSpacing(2)
        self.category_label = QLabel("")
        self.category_label.setObjectName("categoryTag")
        self.theme_name_label = QLabel("")
        self.theme_name_label.setObjectName("themeName")
        self.price_label = QLabel("")
        self.price_label.setObjectName("priceLabel")
        self.date_label = QLabel("")
        self.date_label.setObjectName("dateLabel")
        name_price_col.addWidget(self.category_label)
        name_price_col.addWidget(self.theme_name_label)
        name_price_col.addWidget(self.price_label)
        name_price_col.addWidget(self.date_label)
        info_row.addLayout(name_price_col)
        info_row.addStretch()
        bottom_layout.addLayout(info_row)

        self.layers_summary_label = QLabel("")
        self.layers_summary_label.setObjectName("layersSummary")
        bottom_layout.addWidget(self.layers_summary_label)

        self.layers_container = QWidget()
        self.layers_container_layout = QVBoxLayout(self.layers_container)
        self.layers_container_layout.setContentsMargins(0, 0, 0, 0)
        self.layers_container_layout.setSpacing(8)
        bottom_layout.addWidget(self.layers_container)

        bottom_scroll.setWidget(bottom_container)
        preview_layout.addWidget(bottom_scroll)

        self.buy_btn = QPushButton("Comprar")
        self.buy_btn.setObjectName("buyBtn")
        self.buy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.buy_btn.setEnabled(False)
        preview_layout.addWidget(self.buy_btn)

        body.addWidget(self.preview_card, 1)
        outer.addLayout(body, 1)

        # ---------- rodapé ----------
        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        outer.addWidget(self.status_label)

        self.refresh_btn.clicked.connect(self.load_themes)
        self.search_edit.textChanged.connect(self.filter_themes)
        self.list_widget.currentItemChanged.connect(self.on_select)
        self.buy_btn.clicked.connect(self.on_buy)

        self.load_themes()

    def raw_url(self, path):
        return f"https://raw.githubusercontent.com/{SHOP_OWNER}/{SHOP_REPO}/main/{path}"

    # ---------- listar temas ----------
    def load_themes(self):
        self.status_label.setText("Carregando…")
        url = QUrl(f"https://api.github.com/repos/{SHOP_OWNER}/{SHOP_REPO}/contents/themes/index.json")
        req = QNetworkRequest(url)
        # Esse cabeçalho faz a API do GitHub devolver o conteúdo do arquivo
        # direto, sem precisar decodificar nada — e essa rota não tem o
        # cache agressivo do link "raw", então sempre vem a versão mais nova.
        req.setRawHeader(b"Accept", b"application/vnd.github.v3.raw")
        req.setAttribute(QNetworkRequest.Attribute.CacheLoadControlAttribute, QNetworkRequest.CacheLoadControl.AlwaysNetwork)
        reply = self.manager.get(req)
        reply.finished.connect(lambda: self.on_themes_loaded(reply))

    def on_themes_loaded(self, reply):
        if reply.error() != QNetworkReply.NetworkError.NoError:
            self.status_label.setText("Não foi possível carregar os temas agora.")
            reply.deleteLater()
            return
        try:
            data = json.loads(bytes(reply.readAll()).decode("utf-8"))
        except Exception:
            self.status_label.setText("Não foi possível carregar os temas agora.")
            reply.deleteLater()
            return

        self.themes = data
        self.status_label.setText(f"{len(data)} tema(s) disponível(is)." if data else "Nenhum tema publicado ainda.")
        self._rebuild_list(data)
        reply.deleteLater()

        if self.list_widget.count():
            self.list_widget.setCurrentRow(0)

    def _rebuild_list(self, themes):
        self.list_widget.clear()
        self.themes_by_id = {}
        for theme in themes:
            self.themes_by_id[theme["id"]] = theme
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, theme["id"])
            item.setSizeHint(QSize(220, 68))
            self.list_widget.addItem(item)

            card = ThemeCard(theme)
            self.list_widget.setItemWidget(item, card)
            self._fetch_card_thumbnail(theme, card)

    def _fetch_card_thumbnail(self, theme, card):
        thumb_url = theme.get("thumb_url")
        if not thumb_url:
            return
        req = QNetworkRequest(QUrl(thumb_url))
        reply = self.manager.get(req)
        self.thumb_replies.append(reply)

        def _done():
            if reply.error() == QNetworkReply.NetworkError.NoError:
                pixmap = QPixmap()
                pixmap.loadFromData(bytes(reply.readAll()))
                if not pixmap.isNull():
                    card.set_thumbnail(pixmap)
            reply.deleteLater()

        reply.finished.connect(_done)

    # ---------- busca ----------
    def on_category_filter(self, label):
        self.active_category = None if label == "Todos" else label
        for lbl, btn in self.category_buttons.items():
            btn.setChecked(lbl == label)
        self.filter_themes(self.search_edit.text())

    def filter_themes(self, text):
        text = text.strip().lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            theme = self.themes_by_id.get(item.data(Qt.ItemDataRole.UserRole), {})
            matches_text = (not text) or text in f"{theme.get('name', '')} {theme.get('category', '')}".lower()
            matches_category = (not self.active_category) or theme.get("category") == self.active_category
            item.setHidden(not (matches_text and matches_category))

    def _populate_layers_info(self, layers_info):
        # limpa o que tinha antes
        while self.layers_container_layout.count():
            item = self.layers_container_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not layers_info:
            self.layers_summary_label.setText("")
            return

        n = len(layers_info)
        self.layers_summary_label.setText(f"{n} estilo{'s' if n != 1 else ''} neste tema:")

        bar_width = max(self.preview_card.width() - 56, 180)

        for info in layers_info:
            row = QWidget()
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(3)

            count = info.get("category_count") or 0
            text = info.get("name", "")
            if count:
                plural = "categoria" if count == 1 else "categorias"
                text += f" — {count} {plural}"

            name_row = QHBoxLayout()
            name_row.setSpacing(5)
            name_label = QLabel(text)
            name_label.setObjectName("layerRowName")
            name_row.addWidget(name_label)

            if info.get("has_symbology"):
                sym_icon = QLabel()
                sym_icon.setPixmap(make_symbology_icon(14))
                sym_icon.setToolTip("Simbologia configurada")
                name_row.addWidget(sym_icon)

            if info.get("has_labels"):
                lbl_icon = QLabel()
                lbl_icon.setPixmap(make_labels_icon(14))
                lbl_icon.setToolTip("Rótulos configurados")
                name_row.addWidget(lbl_icon)

            name_row.addStretch()
            row_layout.addLayout(name_row)

            colors = info.get("colors") or []
            if colors:
                bar_label = QLabel()
                bar_label.setFixedHeight(14)
                bar_label.setPixmap(make_color_bar_pixmap(colors, bar_width, height=14))
                row_layout.addWidget(bar_label)

            self.layers_container_layout.addWidget(row)

        self.layers_container_layout.addStretch()

    # ---------- prévia grande ----------
    def on_select(self, current, previous):
        if current is None:
            return
        theme_id = current.data(Qt.ItemDataRole.UserRole)
        self.current_theme = self.themes_by_id.get(theme_id)
        if not self.current_theme:
            return

        self.theme_name_label.setText(self.current_theme["name"])
        self.category_label.setText(self.current_theme.get("category", "").upper())
        self.category_label.setVisible(bool(self.current_theme.get("category")))
        self.price_label.setText("Grátis" if self.current_theme.get("free") else self.current_theme.get("price", ""))
        created = format_date(self.current_theme.get("created_at"))
        self.date_label.setText(f"Publicado em {created}" if created else "")

        self._populate_layers_info(self.current_theme.get("layers_info") or [])

        is_free = bool(self.current_theme.get("free"))
        self.buy_btn.setText("Baixar grátis" if is_free else "Comprar")
        self.buy_btn.setEnabled(is_free or bool(self.current_theme.get("buy_url")))

        thumb_url = self.current_theme.get("thumb_url")
        if not thumb_url:
            self.preview_view.set_empty_message("Sem prévia")
            return

        self.preview_view.set_empty_message("Carregando…")
        req = QNetworkRequest(QUrl(thumb_url))
        reply = self.manager.get(req)
        reply.finished.connect(lambda: self.on_preview_loaded(reply, theme_id))

    def on_preview_loaded(self, reply, theme_id):
        # ignora respostas de seleções antigas (usuário já clicou em outro tema)
        if not self.current_theme or self.current_theme.get("id") != theme_id:
            reply.deleteLater()
            return
        if reply.error() != QNetworkReply.NetworkError.NoError:
            self.preview_view.set_empty_message("Não foi possível carregar a prévia.")
            reply.deleteLater()
            return
        pixmap = QPixmap()
        pixmap.loadFromData(bytes(reply.readAll()))
        if not pixmap.isNull():
            self.preview_view.set_image(pixmap)
        reply.deleteLater()

    # ---------- comprar / baixar grátis ----------
    def on_buy(self):
        if not self.current_theme:
            return
        if self.current_theme.get("free"):
            self._start_free_download()
            return

        raw_url = (self.current_theme.get("buy_url") or "").strip()
        if not raw_url:
            return

        # Corrige links sem "http(s)://" na frente, e tira espaços que às
        # vezes sobram de copiar e colar.
        if not raw_url.lower().startswith(("http://", "https://")):
            raw_url = "https://" + raw_url

        opened = QDesktopServices.openUrl(QUrl(raw_url))
        if not opened:
            QMessageBox.information(
                self,
                "Tessela",
                "Não consegui abrir o navegador automaticamente. Copie o link abaixo e cole no navegador:\n\n"
                + raw_url,
            )

    def _start_free_download(self):
        files = self.current_theme.get("free_files") or []
        if not files:
            QMessageBox.information(self, "Tessela", "Esse tema ainda não tem arquivo disponível para baixar.")
            return

        self.status_label.setText("Baixando…")
        self.buy_btn.setEnabled(False)
        self._free_results = []
        self._free_pending = len(files)

        for f in files:
            req = QNetworkRequest(QUrl(f["qml_url"]))
            reply = self.manager.get(req)
            reply.finished.connect(lambda r=reply, name=f["name"]: self._on_free_file_downloaded(r, name))

    def _on_free_file_downloaded(self, reply, name):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            self._free_results.append((name, bytes(reply.readAll())))
        reply.deleteLater()

        self._free_pending -= 1
        if self._free_pending <= 0:
            self._finish_free_download()

    def _finish_free_download(self):
        self.buy_btn.setEnabled(True)
        results = self._free_results

        if not results:
            self.status_label.setText("Não consegui baixar os arquivos.")
            return

        theme_name = self.current_theme["name"]

        if len(results) == 1:
            name, data = results[0]
            safe = "".join(c for c in name if c.isalnum() or c in "-_") or "estilo"
            path, _ = QFileDialog.getSaveFileName(self, "Salvar estilo", f"{safe}.qml", "Arquivos QML (*.qml)")
            if not path:
                self.status_label.setText("Download cancelado.")
                return
            with open(path, "wb") as fp:
                fp.write(data)
            self.status_label.setText(f"Salvo em: {path}")
            return

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, data in results:
                safe = "".join(c for c in name if c.isalnum() or c in "-_") or "estilo"
                zf.writestr(f"{safe}.qml", data)

        safe_theme = "".join(c for c in theme_name if c.isalnum() or c in "-_ ") or "tema"
        path, _ = QFileDialog.getSaveFileName(self, "Salvar tema", f"{safe_theme}.zip", "Arquivos ZIP (*.zip)")
        if not path:
            self.status_label.setText("Download cancelado.")
            return
        with open(path, "wb") as fp:
            fp.write(buf.getvalue())
        self.status_label.setText(f"Salvo em: {path}")
