"""Script to generate the official TRIAD application icon.

Outputs:
- assets/triad.ico (Multi-resolution Windows Icon: 16, 32, 48, 64, 128, 256 px)
- assets/triad.png (High-resolution 256x256 Master PNG)
"""

import math
import os
from pathlib import Path
import struct
from PySide6.QtCore import QBuffer, QIODevice, QPointF, QPolygonF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QImage,
    QLinearGradient,
    QPainter,
    QPen,
)


def render_icon(size: int) -> QImage:
    """Renders the TRIAD logo at the requested square resolution."""
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(Qt.transparent)

    painter = QPainter(img)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

    scale = size / 256.0

    # 1. Background Squircle (Dark Graphite with Subtle Border)
    margin = 8.0 * scale
    rect = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)
    corner_radius = 52.0 * scale

    bg_gradient = QLinearGradient(0, 0, size, size)
    bg_gradient.setColorAt(0.0, QColor(22, 29, 39))   # #161D27
    bg_gradient.setColorAt(1.0, QColor(11, 15, 20))   # #0B0F14

    painter.setPen(QPen(QColor(43, 53, 67), 2.5 * scale))  # #2B3543 border
    painter.setBrush(QBrush(bg_gradient))
    painter.drawRoundedRect(rect, corner_radius, corner_radius)

    # 2. Geometry calculations
    center_x = size / 2.0
    center_y = size * 0.54
    radius = 62.0 * scale

    # Triad formation: Top (-90 deg), Bottom-Left (150 deg), Bottom-Right (30 deg)
    p_top = QPointF(center_x, center_y - radius * 1.08)
    p_bl = QPointF(
        center_x - radius * math.cos(math.radians(30)),
        center_y + radius * math.sin(math.radians(30)),
    )
    p_br = QPointF(
        center_x + radius * math.cos(math.radians(30)),
        center_y + radius * math.sin(math.radians(30)),
    )
    p_center = QPointF(center_x, center_y)

    # 3. Interconnecting Network Tracks & Spoke Channels
    # Spokes to center
    painter.setPen(QPen(QColor(51, 65, 85, 180), max(1.5, 2.0 * scale)))
    painter.drawLine(p_top, p_center)
    painter.drawLine(p_bl, p_center)
    painter.drawLine(p_br, p_center)

    # Outer perimeter triangle track
    painter.setPen(
        QPen(
            QColor(71, 85, 105, 220),
            max(1.5, 3.5 * scale),
            Qt.SolidLine,
            Qt.RoundCap,
            Qt.RoundJoin,
        )
    )
    triangle = QPolygonF([p_top, p_bl, p_br, p_top])
    painter.setBrush(Qt.NoBrush)
    painter.drawPolyline(triangle)

    # 4. Central Consensus Nexus Core
    core_rad = max(2.5, 8.0 * scale)
    painter.setPen(QPen(QColor(255, 255, 255, 140), max(1.0, 1.5 * scale)))
    painter.setBrush(QBrush(QColor(34, 197, 94)))  # Consensus Green #22C55E
    painter.drawEllipse(p_center, core_rad, core_rad)

    # 5. Three Distinct AI Agent Nodes
    nodes = [
        (p_top, QColor(16, 163, 127), "ChatGPT"),  # Teal #10A37F
        (p_bl, QColor(217, 119, 87), "Claude"),    # Amber/Coral #D97757
        (p_br, QColor(66, 133, 244), "Gemini"),   # Google Blue #4285F4
    ]

    node_rad = max(3.0, 15.0 * scale)
    glow_rad = node_rad * 1.55
    inner_rad = max(1.2, 5.0 * scale)

    for pt, col, _ in nodes:
        # Subtle outer halo glow
        glow_col = QColor(col.red(), col.green(), col.blue(), 55)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(glow_col))
        painter.drawEllipse(pt, glow_rad, glow_rad)

        # Main node sphere with subtle border
        painter.setPen(QPen(QColor(255, 255, 255, 180), max(1.0, 1.8 * scale)))
        painter.setBrush(QBrush(col))
        painter.drawEllipse(pt, node_rad, node_rad)

        # Bright inner core highlight
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(255, 255, 255, 220)))
        painter.drawEllipse(pt, inner_rad, inner_rad)

    painter.end()
    return img


def generate_all_icons(target_dir: Path) -> None:
    """Generates assets/triad.png and assets/triad.ico with all standard resolutions."""
    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. Master PNG (256x256)
    master_png = render_icon(256)
    png_path = target_dir / "triad.png"
    master_png.save(str(png_path), "PNG")

    # 2. Multi-Resolution Windows ICO (256, 128, 64, 48, 32, 16)
    resolutions = [256, 128, 64, 48, 32, 16]
    png_frames = {}

    for res in resolutions:
        im = render_icon(res)
        buf = QBuffer()
        buf.open(QIODevice.WriteOnly)
        im.save(buf, "PNG")
        png_frames[res] = bytes(buf.data())
        buf.close()

    # Construct Windows ICO binary
    count = len(png_frames)
    header = struct.pack("<HHH", 0, 1, count)
    offset = 6 + count * 16
    entries = bytearray()
    images = bytearray()

    for size, data in png_frames.items():
        w = 0 if size >= 256 else size
        h = 0 if size >= 256 else size
        entry = struct.pack(
            "<BBBBHHII",
            w,
            h,
            0,
            0,
            1,
            32,
            len(data),
            offset + len(images),
        )
        entries.extend(entry)
        images.extend(data)

    ico_path = target_dir / "triad.ico"
    with open(ico_path, "wb") as f:
        f.write(header + entries + images)

    print(f"Generated {png_path} ({os.path.getsize(png_path):,} bytes)")
    print(f"Generated {ico_path} ({os.path.getsize(ico_path):,} bytes) with resolutions: {resolutions}")


if __name__ == "__main__":
    assets_dir = Path(__file__).resolve().parent.parent / "assets"
    generate_all_icons(assets_dir)

