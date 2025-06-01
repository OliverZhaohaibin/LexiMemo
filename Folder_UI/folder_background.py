from PySide6.QtCore import QRect, QPropertyAnimation, QEasingCurve, QAbstractAnimation
from PySide6.QtWidgets import QFrame, QGraphicsOpacityEffect


class FolderBackground(QFrame):
    """文件夹子按钮背景框类"""
    def __init__(self, parent):
        super().__init__(parent)
        self.setStyleSheet("background-color: rgba(240, 240, 240, 0.5); border: 2px dashed #888888;")
        self.setFrameShape(QFrame.Box)
        self.lower()  # 确保背景框在按钮下方
        self.hide()

def calculate_folder_background_rect(folder_button, sub_buttons, button_width, button_height, spacing):
    """计算文件夹背景框的矩形区域"""
    if not folder_button.is_expanded or not sub_buttons:
        return None
    
    # 计算包含所有子按钮的矩形区域
    visible_sub_buttons = [btn for btn in sub_buttons if btn.isVisible()]
    if not visible_sub_buttons:
        return None
        
    min_x = min([btn.x() for btn in visible_sub_buttons])
    min_y = min([btn.y() for btn in visible_sub_buttons])
    max_x = max([btn.x() + button_width for btn in visible_sub_buttons])
    max_y = max([btn.y() + button_height for btn in visible_sub_buttons])
    
    # 添加边距
    margin = spacing // 2
    return QRect(min_x - margin, min_y - margin, max_x - min_x + margin * 2, max_y - min_y + margin * 2)

def update_folder_background(app, folder_button):
    """
    更新单个文件夹的灰色背景框 —— 带动画：
      • 位置/尺寸变化：250 ms OutCubic
      • 显示时淡入：250 ms OutQuad
      • 隐藏时淡出：200 ms InQuad
    """

    # 1. 初次创建背景框
    if not hasattr(folder_button, "background_frame"):
        folder_button.background_frame = FolderBackground(app.scroll_content)
        folder_button.background_frame.lower()

        # 绑定透明度效果（适用于子控件）
        effect = QGraphicsOpacityEffect(folder_button.background_frame)
        effect.setOpacity(1.0)
        folder_button.background_frame.setGraphicsEffect(effect)

    frame = folder_button.background_frame
    effect = frame.graphicsEffect()  # type: QGraphicsOpacityEffect

    # 2. 计算应否显示以及目标矩形
    target_rect = calculate_folder_background_rect(
        folder_button,
        folder_button.sub_buttons,
        app.button_width,
        app.button_height,
        app.spacing,
    )

    # ---------- 需要显示 / 更新 ---------- #
    if folder_button.is_expanded and folder_button.sub_buttons and target_rect:
        # 几何动画（尺寸 / 位置）
        if frame.geometry() != target_rect:
            geom_anim = QPropertyAnimation(frame, b"geometry", frame)
            geom_anim.setDuration(250)
            geom_anim.setEasingCurve(QEasingCurve.OutCubic)
            geom_anim.setStartValue(frame.geometry() if frame.isVisible() else target_rect)
            geom_anim.setEndValue(target_rect)
            geom_anim.start(QAbstractAnimation.DeleteWhenStopped)

        # 若当前隐藏 → 淡入
        if frame.isHidden():
            frame.setGeometry(target_rect)
            frame.show()
            effect.setOpacity(0.0)

            fade_in = QPropertyAnimation(effect, b"opacity", frame)
            fade_in.setDuration(250)
            fade_in.setEasingCurve(QEasingCurve.OutQuad)
            fade_in.setStartValue(0.0)
            fade_in.setEndValue(1.0)
            fade_in.start(QAbstractAnimation.DeleteWhenStopped)

    # ---------- 需要隐藏 ---------- #
    else:
        if frame.isVisible():
            fade_out = QPropertyAnimation(effect, b"opacity", frame)
            fade_out.setDuration(200)
            fade_out.setEasingCurve(QEasingCurve.InQuad)
            fade_out.setStartValue(effect.opacity())
            fade_out.setEndValue(0.0)

            def _after_hide():
                frame.hide()
                effect.setOpacity(1.0)  # 复位，以便下次直接显示

            fade_out.finished.connect(_after_hide)
            fade_out.start(QAbstractAnimation.DeleteWhenStopped)

def update_all_folder_backgrounds(app, button_width, button_height):
    """更新所有文件夹的背景框"""
    # 先隐藏所有背景框，确保Z顺序正确
    for btn in app.buttons:
        if btn.is_folder and hasattr(btn, 'background_frame'):
            btn.background_frame.lower()
    
    # 然后更新所有文件夹背景
    for btn in app.buttons:
        if btn.is_folder:
            update_folder_background(app, btn)