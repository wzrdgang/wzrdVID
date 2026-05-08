"""Visual theme for WZRD.VID."""

import platform
from pathlib import Path


def _ui_asset(name: str) -> str:
    return (Path(__file__).resolve().parent / "assets" / "ui" / name).as_posix()


SANS_FONT_STACK = '"Avenir Next", "Helvetica Neue", "Segoe UI", Arial, sans-serif'

if platform.system() == "Darwin":
    MONO_FONT_STACK = 'Menlo, Monaco, "JetBrains Mono", "Cascadia Mono", Consolas, "DejaVu Sans Mono", "Liberation Mono", monospace'
elif platform.system() == "Windows":
    MONO_FONT_STACK = '"Cascadia Mono", Consolas, "JetBrains Mono", "DejaVu Sans Mono", "Liberation Mono", Menlo, Monaco, monospace'
else:
    MONO_FONT_STACK = '"DejaVu Sans Mono", "Liberation Mono", "JetBrains Mono", "Cascadia Mono", Consolas, Menlo, Monaco, monospace'


PALETTE = {
    "black": "#090807",
    "ink": "#16110f",
    "off_white": "#fff9ed",
    "paper": "#fff3de",
    "pink": "#f6b8d4",
    "pink_hot": "#ff7fb9",
    "mint": "#baf4c8",
    "mint_deep": "#75d992",
    "cream": "#ffe8c8",
    "muted": "#5c5049",
    "disabled": "#b9aba1",
}

UI_CONTAMINATION_LEVEL = "industrial_print_damage"
CLEAN_UI_MODE = False


def app_stylesheet() -> str:
    """Return the WZRD.VID Qt stylesheet."""
    paper_noise = _ui_asset("paper_noise_tile.png")
    speckle = _ui_asset("mint_pink_speckle.png")
    swoosh_mint = _ui_asset("cup_swoosh_mint.png")
    swoosh_pink = _ui_asset("cup_swoosh_pink.png")
    halftone = _ui_asset("halftone_edge.png")
    block_noise = _ui_asset("block_noise_strip.png")
    distressed_corner = _ui_asset("distressed_corner.png")
    deck_footer = _ui_asset("deck_footer_wear.png")
    registration = _ui_asset("registration_marks.png")
    jazz_backdrop = _ui_asset("paper_noise_tile.png") if CLEAN_UI_MODE else _ui_asset("jazz_backdrop_field.png")
    artifact_surface = _ui_asset("paper_noise_tile.png") if CLEAN_UI_MODE else _ui_asset("artifact_surface_field.png")
    header_broadcast = _ui_asset("mint_pink_speckle.png") if CLEAN_UI_MODE else _ui_asset("header_broadcast_field.png")
    panel_overprint = _ui_asset("mint_pink_speckle.png") if CLEAN_UI_MODE else _ui_asset("panel_overprint_field.png")
    panel_pink = _ui_asset("mint_pink_speckle.png") if CLEAN_UI_MODE else _ui_asset("panel_surface_pink.png")
    panel_mint = _ui_asset("mint_pink_speckle.png") if CLEAN_UI_MODE else _ui_asset("panel_surface_mint.png")
    panel_cream = _ui_asset("mint_pink_speckle.png") if CLEAN_UI_MODE else _ui_asset("panel_surface_cream.png")
    panel_washed = _ui_asset("mint_pink_speckle.png") if CLEAN_UI_MODE else _ui_asset("panel_surface_washed.png")
    black_bar = _ui_asset("block_noise_strip.png") if CLEAN_UI_MODE else _ui_asset("black_bar_broadcast.png")
    edge_wear = _ui_asset("halftone_edge.png") if CLEAN_UI_MODE else _ui_asset("edge_wear_tile.png")
    scroll_wear = _ui_asset("paper_noise_tile.png") if CLEAN_UI_MODE else _ui_asset("scroll_wear_field.png")
    control_patina = _ui_asset("paper_noise_tile.png") if CLEAN_UI_MODE else _ui_asset("dense_control_patina_tile.png")
    button_print = _ui_asset("paper_noise_tile.png") if CLEAN_UI_MODE else _ui_asset("button_print_tile.png")
    table_static = _ui_asset("paper_noise_tile.png") if CLEAN_UI_MODE else _ui_asset("table_static_tile.png")
    log_static = _ui_asset("paper_noise_tile.png") if CLEAN_UI_MODE else _ui_asset("log_static_tile.png")
    slider_texture = _ui_asset("paper_noise_tile.png") if CLEAN_UI_MODE else _ui_asset("slider_track_texture.png")
    return f"""
    QMainWindow, QScrollArea, QWidget {{
        background: {PALETTE["paper"]};
        color: {PALETTE["black"]};
        font-family: {SANS_FONT_STACK};
        font-size: 14px;
    }}

    QWidget#appRoot, QWidget#tabSurface {{
        background-color: {PALETTE["paper"]};
        background-image: url("{artifact_surface}");
    }}

    QScrollArea {{
        border: 0;
        background-color: {PALETTE["paper"]};
        background-image: url("{artifact_surface}");
    }}

    QScrollArea > QWidget > QWidget {{
        background-image: url("{artifact_surface}");
    }}

    QLabel {{
        color: {PALETTE["black"]};
        background: transparent;
    }}

    QWidget#decorRow {{
        background: transparent;
    }}


    QWidget#headerPanel {{
        background-color: {PALETTE["pink"]};
        background-image: url("{header_broadcast}");
        border: 4px solid {PALETTE["black"]};
        border-radius: 18px;
    }}

    QLabel#logoImage {{
        color: {PALETTE["black"]};
        background: transparent;
        border: 0;
        padding: 0;
        font-family: {MONO_FONT_STACK};
        font-size: 48px;
        font-weight: 900;
        letter-spacing: 0;
    }}

    QLabel#tagline {{
        color: {PALETTE["black"]};
        font-size: 16px;
        font-weight: 900;
        padding: 0 2px;
    }}

    QLabel#rulerStrip {{
        background-color: {PALETTE["cream"]};
        background-image: url("{edge_wear}");
        color: {PALETTE["muted"]};
        border: 2px solid {PALETTE["black"]};
        border-radius: 10px;
        padding: 3px 8px;
        font-family: {MONO_FONT_STACK};
        font-size: 10px;
        font-weight: 900;
    }}

    QLabel#headerBadge {{
        background-color: {PALETTE["black"]};
        background-image: url("{black_bar}");
        color: {PALETTE["off_white"]};
        border: 3px solid {PALETTE["black"]};
        border-radius: 12px;
        padding: 7px 9px;
        font-family: {MONO_FONT_STACK};
        font-size: 12px;
        font-weight: 900;
    }}

    QLabel#staticField {{
        background-color: transparent;
        background-image: url("{swoosh_mint}");
        color: {PALETTE["ink"]};
        border: 0;
        padding: 0 8px;
        font-family: {MONO_FONT_STACK};
        font-size: 10px;
        font-weight: 900;
    }}

    QLabel#terminalStrip {{
        background-color: {PALETTE["black"]};
        background-image: url("{black_bar}");
        color: {PALETTE["mint"]};
        border: 3px solid {PALETTE["black"]};
        border-radius: 12px;
        padding: 6px 9px;
        font-family: {MONO_FONT_STACK};
        font-size: 12px;
        font-weight: 900;
    }}

    QLabel#terminalStrip:hover {{
        color: {PALETTE["pink"]};
    }}

    QLabel#title {{
        font-size: 48px;
        font-weight: 900;
        letter-spacing: 0;
        color: {PALETTE["black"]};
        padding: 0;
    }}

    QLabel#subtitle {{
        color: {PALETTE["muted"]};
        font-size: 17px;
        font-weight: 800;
        padding-bottom: 4px;
    }}

    QLabel#brandBlocks {{
        background-color: {PALETTE["mint"]};
        background-image: url("{black_bar}");
        color: {PALETTE["black"]};
        border: 3px solid {PALETTE["black"]};
        border-radius: 13px;
        padding: 6px 10px;
        font-family: {MONO_FONT_STACK};
        font-size: 12px;
        font-weight: 900;
    }}

    QLabel#presetDescription,
    QLabel#stylePreview {{
        color: {PALETTE["black"]};
        background-color: {PALETTE["cream"]};
        background-image: url("{control_patina}");
        border: 3px solid {PALETTE["black"]};
        border-radius: 12px;
        padding: 8px 10px;
        font-weight: 700;
    }}

    QLabel#stylePreview {{
        background-color: {PALETTE["black"]};
        background-image: url("{log_static}");
        color: {PALETTE["mint"]};
        font-family: {MONO_FONT_STACK};
        font-size: 14px;
        min-height: 34px;
    }}

    QLabel#estimate {{
        color: {PALETTE["black"]};
        background-color: {PALETTE["mint"]};
        background-image: url("{control_patina}");
        border: 2px solid {PALETTE["black"]};
        border-radius: 12px;
        padding: 8px 11px;
        font-weight: 900;
    }}

    QLabel#muted {{
        color: {PALETTE["muted"]};
        font-weight: 700;
    }}


    QTabWidget::pane {{
        border: 4px solid {PALETTE["black"]};
        border-radius: 16px;
        background-color: {PALETTE["paper"]};
        background-image: url("{artifact_surface}");
        top: 0;
    }}

    QTabBar::tab {{
        background-color: {PALETTE["off_white"]};
        background-image: url("{control_patina}");
        color: {PALETTE["black"]};
        border: 3px solid {PALETTE["black"]};
        border-bottom: 0;
        border-top-left-radius: 13px;
        border-top-right-radius: 13px;
        min-width: 104px;
        padding: 8px 17px;
        margin-right: 8px;
        font-weight: 900;
        font-size: 13px;
    }}

    QTabBar::tab:selected {{
        background-color: {PALETTE["mint"]};
        background-image: url("{black_bar}");
    }}

    QTabBar::tab:hover {{
        background-color: {PALETTE["pink"]};
        background-image: url("{button_print}");
    }}

    QLabel#preview {{
        background-color: {PALETTE["off_white"]};
        background-image: url("{table_static}");
        border: 3px solid {PALETTE["black"]};
        border-radius: 13px;
        color: {PALETTE["muted"]};
        font-family: {MONO_FONT_STACK};
        font-size: 15px;
        font-weight: 900;
        padding: 10px;
    }}

    QLabel#pixelStrip {{
        background-color: {PALETTE["black"]};
        background-image: url("{black_bar}");
        color: {PALETTE["mint"]};
        border: 3px solid {PALETTE["black"]};
        border-radius: 12px;
        padding: 6px 10px;
        font-family: {MONO_FONT_STACK};
        font-size: 12px;
        font-weight: 900;
    }}

    QLabel#pixelStrip:disabled {{
        color: {PALETTE["disabled"]};
    }}

    QLabel#artifactStrip {{
        background-color: {PALETTE["cream"]};
        background-image: url("{edge_wear}");
        color: {PALETTE["muted"]};
        border: 2px solid {PALETTE["black"]};
        border-radius: 10px;
        padding: 3px 9px;
        font-family: {MONO_FONT_STACK};
        font-size: 10px;
        font-weight: 900;
    }}

    QLabel#swooshBand {{
        background-color: transparent;
        background-image: url("{header_broadcast}");
        border: 0;
        padding: 0;
    }}

    QLabel#cornerStatic {{
        background-color: transparent;
        background-image: url("{registration}");
        color: {PALETTE["black"]};
        font-family: {MONO_FONT_STACK};
        font-size: 10px;
        font-weight: 900;
        padding: 0;
    }}

    QLabel#deadZoneStrip {{
        background-color: transparent;
        background-image: url("{edge_wear}");
        border: 0;
        padding: 0;
    }}

    QLabel#deckFooter {{
        background-color: {PALETTE["cream"]};
        background-image: url("{edge_wear}");
        color: {PALETTE["muted"]};
        border: 2px solid {PALETTE["black"]};
        border-radius: 9px;
        padding: 3px 8px;
        font-family: {MONO_FONT_STACK};
        font-size: 10px;
        font-weight: 900;
    }}

    QGroupBox {{
        border: 4px solid {PALETTE["black"]};
        border-radius: 18px;
        margin-top: 12px;
        padding: 16px 12px 12px 12px;
        font-size: 15px;
        font-weight: 900;
        background-color: rgba(246, 184, 212, 196);
        background-image: url("{panel_pink}");
        color: {PALETTE["black"]};
    }}

    QGroupBox#sourcePanel,
    QGroupBox#stylePanel,
    QGroupBox#outputPanel {{
        background-color: rgba(246, 184, 212, 174);
        background-image: url("{panel_pink}");
    }}

    QGroupBox#timePanel,
    QGroupBox#outputSizePanel,
    QGroupBox#optimizePanel {{
        background-color: rgba(255, 232, 200, 190);
        background-image: url("{panel_cream}");
    }}

    QGroupBox#framingPanel,
    QGroupBox#batchPanel {{
        background-color: rgba(186, 244, 200, 146);
        background-image: url("{panel_mint}");
    }}

    QGroupBox#blockDetailPanel,
    QGroupBox#coveragePanel,
    QGroupBox#transitionPanel,
    QGroupBox#endingPanel {{
        background-color: rgba(246, 184, 212, 170);
        background-image: url("{panel_washed}");
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 16px;
        padding: 3px 10px;
        background-color: {PALETTE["black"]};
        background-image: url("{black_bar}");
        color: {PALETTE["off_white"]};
        border-radius: 9px;
        font-size: 14px;
        font-weight: 900;
    }}

    QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
        background-color: {PALETTE["off_white"]};
        background-image: url("{control_patina}");
        border: 3px solid {PALETTE["black"]};
        border-radius: 12px;
        padding: 6px 9px;
        color: {PALETTE["black"]};
        font-weight: 700;
        min-height: 22px;
        selection-background-color: {PALETTE["pink_hot"]};
        selection-color: {PALETTE["black"]};
    }}

    QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
        background-color: #ffffff;
        background-image: url("{control_patina}");
        border-color: {PALETTE["pink_hot"]};
    }}

    QTextEdit {{
        font-family: {MONO_FONT_STACK};
        font-size: 12px;
        background-color: {PALETTE["black"]};
        background-image: url("{log_static}");
        color: {PALETTE["mint"]};
        border-radius: 16px;
        padding: 12px;
    }}

    QTableWidget {{
        background-color: {PALETTE["off_white"]};
        background-image: url("{table_static}");
        alternate-background-color: {PALETTE["cream"]};
        border: 3px solid {PALETTE["black"]};
        border-radius: 13px;
        gridline-color: {PALETTE["black"]};
        color: {PALETTE["black"]};
        font-weight: 800;
        selection-background-color: {PALETTE["mint"]};
        selection-color: {PALETTE["black"]};
    }}

    QTableWidget::item {{
        padding: 4px 6px;
        background-image: url("{table_static}");
    }}

    QTableWidget::item:selected {{
        background-color: {PALETTE["mint"]};
        background-image: url("{control_patina}");
    }}

    QTableWidget::indicator {{
        width: 17px;
        height: 17px;
        border: 2px solid {PALETTE["black"]};
        border-radius: 5px;
        background-color: {PALETTE["off_white"]};
        background-image: url("{control_patina}");
    }}

    QTableWidget::indicator:checked {{
        background-color: {PALETTE["pink_hot"]};
        background-image: url("{button_print}");
    }}

    QHeaderView::section {{
        background-color: {PALETTE["black"]};
        background-image: url("{black_bar}");
        color: {PALETTE["off_white"]};
        border: 1px solid {PALETTE["black"]};
        padding: 5px 7px;
        font-family: {MONO_FONT_STACK};
        font-size: 11px;
        font-weight: 900;
    }}

    QComboBox::drop-down {{
        border: 0;
        width: 30px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {PALETTE["off_white"]};
        background-image: url("{control_patina}");
        color: {PALETTE["black"]};
        selection-background-color: {PALETTE["pink"]};
        selection-color: {PALETTE["black"]};
        border: 3px solid {PALETTE["black"]};
        outline: 0;
    }}

    QTableCornerButton::section {{
        background-color: {PALETTE["black"]};
        background-image: url("{black_bar}");
        border: 1px solid {PALETTE["black"]};
    }}

    QPushButton {{
        background-color: {PALETTE["mint"]};
        background-image: url("{button_print}");
        border: 3px solid {PALETTE["black"]};
        border-radius: 13px;
        min-height: 32px;
        padding-left: 12px;
        padding-right: 12px;
        color: {PALETTE["black"]};
        font-size: 12px;
        font-weight: 900;
    }}

    QPushButton:hover {{
        background-color: {PALETTE["pink"]};
        background-image: url("{button_print}");
        border-color: {PALETTE["black"]};
    }}

    QPushButton:pressed {{
        background-color: {PALETTE["pink_hot"]};
        background-image: url("{button_print}");
        padding-top: 3px;
        padding-bottom: 0;
    }}

    QPushButton:disabled {{
        color: {PALETTE["disabled"]};
        background-color: #f0dfd1;
        background-image: url("{control_patina}");
        border-color: {PALETTE["disabled"]};
    }}

    QPushButton#makeButton {{
        background-color: {PALETTE["pink_hot"]};
        background-image: url("{button_print}");
        color: {PALETTE["black"]};
        border-color: {PALETTE["black"]};
        min-height: 46px;
        font-size: 17px;
        border-radius: 16px;
    }}

    QPushButton#secondaryButton {{
        background-color: {PALETTE["off_white"]};
        background-image: url("{control_patina}");
    }}

    QPushButton#dangerButton {{
        background-color: {PALETTE["black"]};
        background-image: url("{black_bar}");
        color: {PALETTE["off_white"]};
    }}

    QCheckBox {{
        spacing: 9px;
        min-height: 22px;
        font-weight: 800;
        color: {PALETTE["black"]};
    }}

    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border: 3px solid {PALETTE["black"]};
        border-radius: 7px;
        background-color: {PALETTE["off_white"]};
        background-image: url("{control_patina}");
    }}

    QCheckBox::indicator:checked {{
        background-color: {PALETTE["pink_hot"]};
        background-image: url("{button_print}");
    }}

    QSlider::groove:horizontal {{
        height: 11px;
        background-color: {PALETTE["off_white"]};
        background-image: url("{slider_texture}");
        border: 3px solid {PALETTE["black"]};
        border-radius: 7px;
    }}

    QSlider::sub-page:horizontal {{
        background-color: {PALETTE["pink_hot"]};
        background-image: url("{slider_texture}");
        border: 3px solid {PALETTE["black"]};
        border-radius: 7px;
    }}

    QSlider::handle:horizontal {{
        background-color: {PALETTE["mint"]};
        background-image: url("{control_patina}");
        border: 3px solid {PALETTE["black"]};
        width: 23px;
        height: 23px;
        margin: -8px 0;
        border-radius: 14px;
    }}

    QProgressBar {{
        border: 3px solid {PALETTE["black"]};
        border-radius: 13px;
        background-color: {PALETTE["off_white"]};
        background-image: url("{control_patina}");
        color: {PALETTE["black"]};
        text-align: center;
        min-height: 30px;
        font-weight: 900;
    }}

    QProgressBar::chunk {{
        background-color: {PALETTE["pink_hot"]};
        background-image: url("{button_print}");
        border-radius: 9px;
        margin: 2px;
    }}

    QFrame#divider {{
        color: {PALETTE["black"]};
        background-color: {PALETTE["black"]};
        background-image: url("{black_bar}");
        max-height: 4px;
        border-radius: 2px;
    }}

    QScrollBar:vertical {{
        background-color: {PALETTE["paper"]};
        background-image: url("{scroll_wear}");
        width: 16px;
        margin: 0;
    }}

    QScrollBar::handle:vertical {{
        background-color: {PALETTE["pink_hot"]};
        background-image: url("{button_print}");
        border: 3px solid {PALETTE["black"]};
        border-radius: 8px;
        min-height: 40px;
    }}

    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    """
