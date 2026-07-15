from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient, QFont, QMouseEvent, QPolygonF
from PyQt6.QtCore import Qt, QPointF, QRectF
import time
from datetime import datetime
from typing import Any, Dict, List, Tuple

class HistoryChartWidget(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.history_data: List[Tuple[float, float]] = []  # List of (timestamp, value_usd)
        self.currency_symbol = "$"
        self.exchange_rate = 1.0
        
        # UI/Hover state
        self.setMouseTracking(True)
        self.hover_index: int | None = None
        self.hover_pos: QPointF | None = None
        
        # Design Constants
        self.COLOR_BG = QColor("#111111")
        self.COLOR_BORDER = QColor("#2f2f2f")
        self.COLOR_GRID = QColor("#1a1a1a")
        self.COLOR_LINE = QColor("#c8a24b")
        self.COLOR_HOVER_LINE = QColor("#f2c94c")
        self.COLOR_TEXT = QColor("#b8b8b8")
        
        # Layout Padding
        self.left_padding = 60
        self.right_padding = 20
        self.top_padding = 25
        self.bottom_padding = 30

    def set_data(self, history: List[Dict[str, Any]], currency_symbol: str, exchange_rate: float) -> None:
        """Sets the valuation history points and currency conversion factors."""
        self.currency_symbol = currency_symbol
        self.exchange_rate = exchange_rate
        
        # Map raw history records into (timestamp, value_in_target_currency)
        self.history_data = []
        for entry in history:
            ts = entry.get("timestamp", 0.0)
            val_usd = entry.get("total_value_usd", 0.0)
            val_converted = val_usd * self.exchange_rate
            self.history_data.append((ts, val_converted))
            
        self.history_data.sort(key=lambda x: x[0])
        self.hover_index = None
        self.hover_pos = None
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self.history_data or len(self.history_data) < 2:
            return
            
        # Get active plot bounds
        w = self.width() - self.left_padding - self.right_padding
        min_time = self.history_data[0][0]
        max_time = self.history_data[-1][0]
        time_range = max_time - min_time if max_time > min_time else 1.0
        
        # Calculate X coordinate for each point to find the closest one to cursor
        x_positions = []
        for ts, _ in self.history_data:
            x = self.left_padding + ((ts - min_time) / time_range) * w
            x_positions.append(x)
            
        mouse_x = event.position().x()
        
        # Find index with smallest horizontal distance
        closest_idx = 0
        min_dist = abs(mouse_x - x_positions[0])
        for idx, x in enumerate(x_positions):
            dist = abs(mouse_x - x)
            if dist < min_dist:
                min_dist = dist
                closest_idx = idx
                
        # Limit hover detection to vertical area of the chart
        if self.left_padding - 10 <= mouse_x <= self.width() - self.right_padding + 10:
            self.hover_index = closest_idx
            self.hover_pos = event.position()
        else:
            self.hover_index = None
            self.hover_pos = None
            
        self.update()

    def leaveEvent(self, event: Any) -> None:
        self.hover_index = None
        self.hover_pos = None
        self.update()

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 1. Background
        painter.fillRect(self.rect(), self.COLOR_BG)
        
        # 2. Draw border
        painter.setPen(QPen(self.COLOR_BORDER, 1))
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)
        
        if not self.history_data:
            # Draw placeholder message
            painter.setPen(self.COLOR_TEXT)
            painter.setFont(QFont("Segoe UI", 11))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No valuation history recorded yet")
            return
            
        # Draw plot area bounds
        plot_w = self.width() - self.left_padding - self.right_padding
        plot_h = self.height() - self.top_padding - self.bottom_padding
        
        # Get min and max limits
        vals = [pt[1] for pt in self.history_data]
        min_val = min(vals)
        max_val = max(vals)
        
        # Add 10% breathing padding to top and bottom of chart Y-axis
        val_range = max_val - min_val
        if val_range < 0.01:
            val_range = 1.0
            min_val = max(0.0, min_val - 0.5)
            max_val = min_val + 1.0
        else:
            min_val = max(0.0, min_val - 0.1 * val_range)
            max_val = max_val + 0.1 * val_range
            val_range = max_val - min_val
            
        min_time = self.history_data[0][0]
        max_time = self.history_data[-1][0]
        time_range = max_time - min_time if max_time > min_time else 1.0
        
        # 3. Draw grid lines (4 horizontal grid lines)
        grid_pen = QPen(self.COLOR_GRID, 1, Qt.PenStyle.DotLine)
        painter.setPen(grid_pen)
        painter.setFont(QFont("Segoe UI", 8))
        
        for i in range(4):
            y_fraction = i / 3.0
            y = self.top_padding + (1 - y_fraction) * plot_h
            painter.drawLine(self.left_padding, int(y), self.width() - self.right_padding, int(y))
            
            # Label
            val_at_grid = min_val + y_fraction * val_range
            painter.setPen(QPen(self.COLOR_TEXT, 1))
            label_text = f"{self.currency_symbol}{val_at_grid:.2f}"
            painter.drawText(
                QRectF(5, y - 8, self.left_padding - 10, 16),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                label_text
            )
            painter.setPen(grid_pen)
            
        # 4. Map data points to screen coordinates
        points = []
        for ts, val in self.history_data:
            x = self.left_padding + ((ts - min_time) / time_range) * plot_w
            y = self.top_padding + (1 - (val - min_val) / val_range) * plot_h
            points.append(QPointF(x, y))
            
        # 5. Draw area gradient under the curve
        if len(points) >= 2:
            gradient_path = QPolygonF()
            gradient_path.append(QPointF(points[0].x(), self.height() - self.bottom_padding))
            for pt in points:
                gradient_path.append(pt)
            gradient_path.append(QPointF(points[-1].x(), self.height() - self.bottom_padding))
            
            gradient = QLinearGradient(0, self.top_padding, 0, self.height() - self.bottom_padding)
            gradient.setColorAt(0.0, QColor(200, 162, 75, 60))  # Semi-transparent gold
            gradient.setColorAt(1.0, QColor(200, 162, 75, 0))   # Fully transparent
            
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(gradient))
            painter.drawPolygon(gradient_path)
            
        # 6. Draw main line
        line_pen = QPen(self.COLOR_LINE, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(line_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for i in range(len(points) - 1):
            painter.drawLine(points[i], points[i+1])
            
        # 7. Draw X-axis timestamps (first and last dates)
        painter.setPen(QPen(self.COLOR_TEXT, 1))
        first_date = datetime.fromtimestamp(min_time).strftime("%Y-%m-%d %H:%M")
        last_date = datetime.fromtimestamp(max_time).strftime("%Y-%m-%d %H:%M")
        
        painter.drawText(
            QRectF(self.left_padding, self.height() - self.bottom_padding + 5, plot_w * 0.4, 20),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            first_date
        )
        painter.drawText(
            QRectF(self.width() - self.right_padding - plot_w * 0.4, self.height() - self.bottom_padding + 5, plot_w * 0.4, 20),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
            last_date
        )
        
        # 8. Render Interactive hover elements (dashed vertical line, dot, and tooltip card)
        if self.hover_index is not None and self.hover_index < len(points):
            pt = points[self.hover_index]
            raw_ts, raw_val = self.history_data[self.hover_index]
            
            # Draw vertical hover indicator line
            painter.setPen(QPen(self.COLOR_HOVER_LINE, 1, Qt.PenStyle.DashLine))
            painter.drawLine(int(pt.x()), self.top_padding, int(pt.x()), self.height() - self.bottom_padding)
            
            # Draw hover dot on curve
            painter.setPen(QPen(self.COLOR_HOVER_LINE, 2))
            painter.setBrush(QBrush(QColor("#0b0b0b")))
            painter.drawEllipse(pt, 5, 5)
            
            # Draw floating Tooltip card
            hover_date = datetime.fromtimestamp(raw_ts).strftime("%Y-%m-%d %H:%M")
            tooltip_lines = [
                f"Date: {hover_date}",
                f"Total: {self.currency_symbol}{raw_val:.2f}"
            ]
            
            # Measure text size
            fm = painter.fontMetrics()
            tw = max(fm.horizontalAdvance(line) for line in tooltip_lines) + 20
            th = len(tooltip_lines) * 16 + 12
            
            # Determine card position to avoid drawing off-screen
            tx = pt.x() + 15
            if tx + tw > self.width() - 10:
                tx = pt.x() - tw - 15
            ty = pt.y() - th / 2
            if ty < 10:
                ty = 10
            elif ty + th > self.height() - 10:
                ty = self.height() - th - 10
                
            tooltip_rect = QRectF(tx, ty, tw, th)
            
            # Draw card frame
            painter.setPen(QPen(self.COLOR_LINE, 1))
            painter.setBrush(QBrush(QColor("#1d1d1d")))
            painter.drawRoundedRect(tooltip_rect, 6, 6)
            
            # Draw card content
            painter.setPen(QPen(QColor("#e8e8e8"), 1))
            for idx, line in enumerate(tooltip_lines):
                painter.drawText(
                    QRectF(tx + 10, ty + 6 + idx * 16, tw - 20, 16),
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    line
                )
