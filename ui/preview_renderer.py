import os
from PySide6.QtGui import QPixmap, QPainter, QFont, QColor
from PySide6.QtCore import Qt
from domain.composition import CompositionPlan

class PreviewRenderer:
    @staticmethod
    def render(plan: CompositionPlan) -> QPixmap:
        """
        Renders the composition plan into a QPixmap overlay with transparent background.
        """
        pix = QPixmap(plan.target_width, plan.target_height)
        pix.fill(Qt.transparent)

        painter = QPainter(pix)

        for element in plan.elements:
            if element.type == "image":
                if not element.content or not os.path.exists(element.content):
                    continue

                img = QPixmap(element.content)
                if img.isNull():
                    continue

                # Scale Image using the calculated image_width
                img = img.scaledToWidth(element.image_width, Qt.SmoothTransformation)

                # Apply coordinates
                x = int((plan.target_width - img.width()) * element.x_pct)
                y = int((plan.target_height - img.height()) * element.y_pct)

                painter.setOpacity(element.opacity)
                painter.drawPixmap(x, y, img)
                painter.setOpacity(1.0)

            elif element.type == "text":
                font = QFont("Arial", element.font_size, QFont.Bold)
                painter.setFont(font)

                # Calculate bounding rect for centering/placement
                fm = painter.fontMetrics()
                br = fm.boundingRect(element.content)
                tw, th = br.width(), br.height()

                x = int((plan.target_width - tw) * element.x_pct)
                y = int((plan.target_height - th) * element.y_pct) + th

                painter.setOpacity(element.opacity)

                if element.shadow:
                    painter.setPen(QColor("black"))
                    painter.drawText(x+1, y+1, element.content)
                    painter.drawText(x-1, y-1, element.content)

                painter.setPen(QColor(element.color))
                painter.drawText(x, y, element.content)

                painter.setOpacity(1.0)

        painter.end()
        return pix
