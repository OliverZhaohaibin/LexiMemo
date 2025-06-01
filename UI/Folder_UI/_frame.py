from PySide6.QtWidgets import QFrame


class ButtonFrame(QFrame):
    """
    自定义框架类，用于显示不同类型的边框提示
    """
    def __init__(self, parent, border_style):
        super().__init__(parent)
        self.setFrameShape(QFrame.Box)
        self.setLineWidth(2)
        self.setStyleSheet(border_style)
        self.hide()