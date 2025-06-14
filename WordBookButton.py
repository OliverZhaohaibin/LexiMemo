# WordBookButton.py开始
from PySide6.QtWidgets import QPushButton, QLineEdit, QMessageBox, QMenu
from PySide6.QtGui import QColor, QPainter, QPixmap, QFont, QCursor
from PySide6.QtCore import Qt, QRect, QPoint, QPropertyAnimation, QTimer, QEasingCurve, Property, Signal, QSize
from PySide6.QtGui import QColorConstants

from PIL import Image
import os
import sys
from font import normal_font
from PySide6.QtGui import QCursor  # Ensure QCursor is imported


class WordBookButton(QPushButton):
    """自定义单词本按钮，支持拖拽、文件夹展开/折叠、子按钮拖出等交互。"""
    nameChangedNeedsLayoutSave = Signal()

    DRAG_THRESHOLD = 5  # Pixels mouse must move to be considered a drag

    def __init__(self, title: str, color: str, parent=None, app=None):  # app is CoverContent
        super().__init__(title, parent)
        self.app = app

        self.color = color
        self.path: str | None = None
        self.is_folder = False
        self.is_expanded = False
        self.is_sub_button = False
        self.parent_folder: WordBookButton | None = None
        self.sub_buttons: list[WordBookButton] = []

        self.is_dragging = False
        self.mouse_press_pos_local: QPoint | None = None  # Store local mouse position on press
        self._cursor_offset = QPoint()
        self.drag_out_threshold_exceeded = False
        self._origin_pos = QPoint()  # Original widget position before drag

        self._rotation = 0.0
        if hasattr(self.app, "button_width") and hasattr(self.app, "button_height"):
            self.setFixedSize(QSize(self.app.button_width, self.app.button_height))
        else:
            self.setFixedSize(QSize(120, 150))

        cover_font = QFont(normal_font)
        cover_font.setBold(True)
        self.setFont(cover_font)
        self.icon_size = self.app.button_width if self.app and hasattr(self.app, 'button_width') else 120

        icon_path = self.create_colored_icon(color)
        self.icon_path = icon_path
        self.icon_pixmap = QPixmap(icon_path).scaled(self.icon_size, self.icon_size, Qt.KeepAspectRatio,
                                                     Qt.SmoothTransformation)

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                text-align: center;
                color: #333333; 
            }}
        """)

        self.name_edit = QLineEdit(self)
        self.name_edit.hide()
        self.name_edit.setAlignment(Qt.AlignCenter)
        self.name_edit.setStyleSheet(
            "QLineEdit { border: 1px solid #888; border-radius: 4px; background-color: rgba(255, 255, 255, 0.9); }")
        self.name_edit.returnPressed.connect(self.finish_name_edit)
        self.name_edit.editingFinished.connect(self.finish_name_edit)
        self.rename_source = "edit"

        self.delete_button = QPushButton("✕", self)
        self.delete_button.setFixedSize(22, 22)
        self.delete_button.setStyleSheet(
            "QPushButton { background-color: #FF4D4D; color: #FFFFFF; border: none; border-radius: 11px; font-weight: bold; } QPushButton:hover { background-color: #FF8080; }")
        self.delete_button.hide()
        self.delete_button.clicked.connect(self.on_delete_clicked)
        self.delete_button.setCursor(Qt.ArrowCursor)

        self.setMouseTracking(True)

        self._fade_opacity: float = 1.0
        self._fade_anim: QPropertyAnimation | None = None
        self._long_press_timer: QTimer | None = None
        self._suppress_dark: bool = False
        self.folder_animation_group = None
        self._recenter_timer: QTimer | None = None

        from PySide6.QtCore import QParallelAnimationGroup
        self.jitter_animation_group = QParallelAnimationGroup(self)
        self.jitter_animations = []
        if not self.is_sub_button:  # 只有主按钮才需要
            self.clicked.connect(self._on_clicked)

        # 同文件，再加一个方法
    def _on_clicked(self, checked=False):
        """
        非编辑模式下，左键单击主文件夹按钮 → 展开 / 折叠。
        其它情况（编辑模式、子按钮）交给原逻辑处理。
        """
        if self.app and not self.app.edit_mode and self.is_folder and not self.is_dragging:
            self.app.toggle_folder(self)
    @staticmethod
    def lighten_color(color_str: str, factor: float = 0.6) -> str:
        q_color = QColor(color_str)
        return q_color.lighter(120 + int(factor * 30)).name()

    def create_colored_icon(self, color: str) -> str:
        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        icon_dir = os.path.join(base_dir, "UI", "word_book_button", "icon")
        os.makedirs(icon_dir, exist_ok=True)

        color_filename_part = color.replace("#", "")
        icon_path = os.path.join(icon_dir, f"colored_icon_{color_filename_part}.png")

        if os.path.exists(icon_path):
            return icon_path

        base_image_path = os.path.join(icon_dir, "cover.webp")
        if not os.path.exists(base_image_path):
            pixmap = QPixmap(QSize(self.icon_size, self.icon_size))
            pixmap.fill(QColor(color))
            pixmap.save(icon_path)
            return icon_path

        base_image = Image.open(base_image_path).convert("RGBA")
        datas = base_image.getdata()
        new_data = []
        target_color_pil = Image.new("RGBA", (1, 1), color).getdata()[0]

        for item in datas:
            if not (item[0] > 200 and item[1] > 200 and item[2] > 200 and item[3] < 50):
                new_data.append(target_color_pil)
            else:
                new_data.append((255, 255, 255, 0))

        base_image.putdata(new_data)
        base_image.save(icon_path)
        return icon_path

    def update_folder_icon(self):
        from UI.folder_ui.api import create_folder_icon

        if not self.is_folder or not self.sub_buttons:
            if not self.is_folder and hasattr(self, 'color'):
                original_icon_path = self.create_colored_icon(self.color)
                self.icon_path = original_icon_path
                self.icon_pixmap = QPixmap(original_icon_path).scaled(self.icon_size, self.icon_size,
                                                                      Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.update()
            return

        sub_icon_paths = [sub.icon_path for sub in self.sub_buttons[:9] if hasattr(sub, 'icon_path') and sub.icon_path]
        if not sub_icon_paths:
            empty_folder_icon_path = self.create_colored_icon(self.color)
            self.icon_path = empty_folder_icon_path
            self.icon_pixmap = QPixmap(empty_folder_icon_path).scaled(self.icon_size, self.icon_size,
                                                                      Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.update()
            return

        icon_path = create_folder_icon(sub_icon_paths=sub_icon_paths, folder_name=self.text())
        self.icon_path = icon_path
        self.icon_pixmap = QPixmap(icon_path).scaled(self.icon_size, self.icon_size, Qt.KeepAspectRatio,
                                                     Qt.SmoothTransformation)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self.underMouse() or (self.isDown() and not self._suppress_dark):
            bg_color_str = self.color if self.isDown() and not self._suppress_dark and self.fadeOpacity > 0.01 else WordBookButton.lighten_color(
                self.color)
            bg_qcolor = QColor(bg_color_str)
            if self.isDown() and not self._suppress_dark:
                bg_qcolor.setAlphaF(self.fadeOpacity)

            painter.setPen(Qt.NoPen)
            painter.setBrush(bg_qcolor)
            painter.drawRoundedRect(self.rect(), 15, 15)

        painter.save()
        if self._rotation != 0:
            painter.translate(self.width() / 2, self.height() / 2)
            painter.rotate(self._rotation)
            painter.translate(-self.width() / 2, -self.height() / 2)

        if hasattr(self, "icon_pixmap") and not self.icon_pixmap.isNull():
            icon_x = (self.width() - self.icon_pixmap.width()) // 2
            icon_y = 0
            painter.drawPixmap(icon_x, icon_y, self.icon_pixmap)
        else:
            painter.setBrush(QColor(self.color))
            painter.drawRect(QRect((self.width() - self.icon_size) // 2, 0, self.icon_size, self.icon_size))

        painter.setPen(
            QColorConstants.Black if self.palette().buttonText().color() == QColorConstants.White else self.palette().buttonText().color())

        text_margin_top = 5
        text_rect_y = self.icon_size + text_margin_top
        text_rect_height = self.height() - text_rect_y - 5
        text_rect = QRect(0, text_rect_y, self.width(), text_rect_height)

        fm = painter.fontMetrics()
        elided_text = fm.elidedText(self.text(), Qt.ElideRight, text_rect.width() - 10)
        painter.drawText(text_rect, Qt.AlignHCenter | Qt.AlignTop, elided_text)

        painter.restore()

    def _update_cursor(self, pos: QPoint):
        if self.app and self.app.edit_mode:
            name_rect = QRect(0, self.icon_size + 5, self.width(), self.height() - self.icon_size - 5)
            if self.delete_button.isVisible() and self.delete_button.geometry().contains(pos):
                self.setCursor(Qt.ArrowCursor)
            elif name_rect.contains(pos):
                self.setCursor(Qt.IBeamCursor)
            else:
                self.setCursor(Qt.PointingHandCursor)
        else:  # Non-edit mode
            self.setCursor(Qt.PointingHandCursor)

    def enterEvent(self, event):
        self._update_cursor(event.pos())
        super().enterEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self.app and self.app.edit_mode and not getattr(self, "is_new_button", False):
            name_rect = QRect(0, self.icon_size + 5, self.width(), self.height() - self.icon_size - 5)
            if name_rect.contains(event.pos()):
                self.start_name_edit()
                return
        # In non-edit mode, or if not clicking the name area,
        # a double click should behave like a single click for folders/wordbooks
        # This is handled by the single click logic in mouseReleaseEvent if not a drag
        # No need to call super().mouseDoubleClickEvent() as it might have unintended default behavior.
        # Instead, ensure our single click logic fires.
        # Let mouseReleaseEvent handle it.
        if event.button() == Qt.LeftButton:
            pass  # Let release handle it

    def start_name_edit(self):
        if getattr(self, "is_new_button", False): return
        self.stop_jitter()
        self.name_edit.setText(self.text())
        self.name_edit.selectAll()
        y_start = self.icon_size + 5
        self.name_edit.setGeometry(0, y_start, self.width(), self.height() - y_start)
        self.name_edit.show()
        QTimer.singleShot(0, self.name_edit.setFocus)

    def finish_name_edit(self):
        if not self.name_edit.isVisible(): return

        new_name = self.name_edit.text().strip()
        self.name_edit.hide()

        if not new_name or new_name == self.text():
            if self.app.edit_mode and self.rename_source == "edit": self.start_jitter()
            return

        sibling_names = [btn.text() for btn in self.app.buttons if btn is not self and not btn.is_sub_button]
        if self.is_sub_button and self.parent_folder:
            sibling_names = [sub.text() for sub in self.parent_folder.sub_buttons if sub is not self]

        if new_name in sibling_names:
            QMessageBox.warning(self, "重名冲突", "已有同名单词本或文件夹！")
            if self.app.edit_mode and self.rename_source == "edit": self.start_jitter()
            return

        old_name = self.text()
        old_path = self.path

        self.setText(new_name)

        if not self.is_folder:
            try:
                new_path = self.rename_wordbook_directory(old_name, new_name)
                self.path = new_path
                if hasattr(self.app, 'show_word_book'):
                    try:
                        self.clicked.disconnect()
                    except RuntimeError:
                        pass
                    self.clicked.connect(lambda checked=False, p=self.path: self.app.show_word_book(p))
            except Exception as e:
                QMessageBox.warning(self, "重命名失败", f"{e}")
                self.setText(old_name)
                self.path = old_path
                if self.app.edit_mode and self.rename_source == "edit": self.start_jitter()
                return
        else:
            self.update_folder_icon()

        if self.is_sub_button and self.parent_folder:
            self.parent_folder.update_folder_icon()

        self.app.update_button_positions()
        self.nameChangedNeedsLayoutSave.emit()

        if self.app.edit_mode and self.rename_source == "edit": self.start_jitter()
        self.rename_source = "edit"

    def rename_wordbook_directory(self, old_name: str, new_name: str) -> str:
        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        books_dir = os.path.join(base_dir, "books")
        old_folder_name = f"books_{old_name}_{self.color}"
        new_folder_name = f"books_{new_name}_{self.color}"
        old_path_on_disk = os.path.join(books_dir, old_folder_name)
        new_path_on_disk = os.path.join(books_dir, new_folder_name)

        if old_path_on_disk == new_path_on_disk: return new_path_on_disk

        if os.path.exists(new_path_on_disk):
            raise FileExistsError(f"目标文件夹 '{new_folder_name}' 已存在。")
        if not os.path.exists(old_path_on_disk):
            os.makedirs(new_path_on_disk, exist_ok=True)
            from db import init_db as db_init_db
            db_init_db(os.path.join(new_path_on_disk, "wordbook.db"))
            return new_path_on_disk

        os.rename(old_path_on_disk, new_path_on_disk)
        return new_path_on_disk

    def on_delete_clicked(self):
        if getattr(self, "is_new_button", False): return
        if self.text() == "总单词册" and not self.is_sub_button:
            QMessageBox.information(self, "提示", "『总单词册』是主单词册，无法删除！")
            return

        if hasattr(self.app, 'delete_word_book'):
            self.app.delete_word_book(self)

    def start_jitter(self):
        if getattr(self, "is_new_button", False): return
        if self.jitter_animation_group.state() == QPropertyAnimation.Running: return

        self.jitter_animation_group.stop()
        self.jitter_animation_group.clear()

        duration = 200
        rotation_angle = 2.0

        anim_rot = QPropertyAnimation(self, b"rotation")
        anim_rot.setDuration(duration)
        anim_rot.setLoopCount(-1)
        anim_rot.setKeyValueAt(0, 0)
        anim_rot.setKeyValueAt(0.3, -rotation_angle)
        anim_rot.setKeyValueAt(0.5, 0)
        anim_rot.setKeyValueAt(0.7, rotation_angle)
        anim_rot.setKeyValueAt(1, 0)
        self.jitter_animation_group.addAnimation(anim_rot)

        self.jitter_animation_group.start()
        self.update_delete_button_visibility()

    def stop_jitter(self):
        if self.jitter_animation_group.state() == QPropertyAnimation.Running:
            self.jitter_animation_group.stop()
        self._rotation = 0
        self.update()
        self.update_delete_button_visibility()

    @Property(float)
    def rotation(self):
        return self._rotation

    @rotation.setter
    def rotation(self, angle):
        self._rotation = angle
        self.update()

    def update_delete_button_visibility(self):
        show = (self.app and self.app.edit_mode and \
                not getattr(self, "is_new_button", False) and \
                not (self.text() == "总单词册" and not self.is_sub_button)
                )

        self.delete_button.move(self.width() - self.delete_button.width() - 2, 2)
        self.delete_button.setVisible(show)
        if show: self.delete_button.raise_()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._start_press_effect()
            self.mouse_press_pos_local = event.position().toPoint()  # Store local press position
            self.is_dragging = False  # Assume it's a click until drag threshold is met

            if self.app and self.app.edit_mode and not getattr(self, "is_new_button", False):
                self._origin_pos = self.pos()
                cursor_global = event.globalPosition().toPoint()
                button_global_tl = self.mapToGlobal(QPoint(0, 0))
                self._cursor_offset = cursor_global - button_global_tl
                self.raise_()  # Raise button for dragging

                # Recenter timer logic only if it's a main button and collapse is needed
                if not self.is_sub_button and hasattr(self.app, 'collapse_all_folders'):
                    scroll_area = getattr(self.app, "scroll_area", None)
                    old_scroll_value = scroll_area.verticalScrollBar().value() if scroll_area else 0
                    self.app.collapse_all_folders()

                    def _reposition_after_collapse():
                        # Check if still valid to reposition (e.g., button still exists, drag ongoing)
                        if not self.is_dragging and self.mouse_press_pos_local is None:  # Check if drag started
                            self._stop_recenter_timer()
                            return
                        if not self.parentWidget():  # Safety check
                            self._stop_recenter_timer()
                            return

                        if scroll_area:
                            current_max_scroll = scroll_area.verticalScrollBar().maximum()
                            scroll_area.verticalScrollBar().setValue(min(old_scroll_value, current_max_scroll))

                        current_mouse_global = QCursor.pos()
                        target_button_global_tl = current_mouse_global - self._cursor_offset
                        new_local_pos = self.parentWidget().mapFromGlobal(target_button_global_tl)

                        if (self.pos() - new_local_pos).manhattanLength() > 1:
                            self.move(new_local_pos)

                    self._recenter_timer = QTimer(self)
                    self._recenter_timer.setInterval(10)
                    self._recenter_timer.timeout.connect(_reposition_after_collapse)
                    self._recenter_timer.start()
                    _reposition_after_collapse()  # Try immediate reposition
                    QTimer.singleShot(800, self._stop_recenter_timer)  # Safety stop
            # For non-edit mode, or "new button", we still call super.mousePressEvent
            # to get the visual "pressed" state. The actual "clicked" signal is emitted on release.
            else:
                super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        from UI.folder_ui.api import calculate_folder_area, calculate_reorder_area
        self._update_cursor(event.pos())

        if not (event.buttons() & Qt.LeftButton and self.app and self.app.edit_mode and \
                not getattr(self, "is_new_button", False)):
            # If not a drag scenario, still call super for other mouse move behaviors
            super().mouseMoveEvent(event)
            return

        # Check drag threshold if not already dragging
        if not self.is_dragging and self.mouse_press_pos_local is not None:
            if (event.position().toPoint() - self.mouse_press_pos_local).manhattanLength() > self.DRAG_THRESHOLD:
                self.is_dragging = True
                # Potentially stop recenter timer here if it was started, as manual drag takes over
                self._stop_recenter_timer()

        if not self.is_dragging:
            # If not dragging yet (threshold not met), let super handle it
            super().mouseMoveEvent(event)
            return

        # --- Actual drag movement logic ---
        current_mouse_global = event.globalPosition().toPoint()
        target_button_global_tl = current_mouse_global - self._cursor_offset

        if self.parentWidget():
            new_local_pos = self.parentWidget().mapFromGlobal(target_button_global_tl)
            self.move(new_local_pos)
        else:
            self.is_dragging = False  # Safety: stop if parent is gone
            return

        # --- Folder interaction logic (only if dragging) ---
        if self.is_sub_button and self.parent_folder:
            reorder_rect = calculate_reorder_area(
                self.parent_folder, self.app.button_width, self.app.button_height,
                self.app.spacing, self.app.scroll_content.width(), getattr(self.app, 'folder_extra_width', 0)
            )
            button_center_in_scroll_content = self.mapTo(self.app, self.rect().center())

            if reorder_rect.contains(button_center_in_scroll_content):
                self.app.show_blue_reorder_frame(self.parent_folder)
                self.app.hide_red_removal_frame()
                self.drag_out_threshold_exceeded = False
                self.app.update_sub_button_order(self.parent_folder, dragged_sub_button=self, realtime=True)
            else:
                self.app.hide_blue_reorder_frame()
                self.app.show_red_removal_frame(self.parent_folder)
                self.drag_out_threshold_exceeded = True
        else:  # Main button drag
            self.app.check_button_proximity(self)
            self.app.update_button_order(self)  # This calls animate_button_positions

    def mouseReleaseEvent(self, event):
        self._stop_recenter_timer()
        self._end_press_effect()

        was_dragging_in_edit_mode = self.is_dragging  # is_dragging is now only true if threshold met

        # Reset dragging state and press position for next interaction
        self.is_dragging = False
        current_mouse_press_pos_local = self.mouse_press_pos_local
        self.mouse_press_pos_local = None

        if event.button() == Qt.LeftButton:
            if was_dragging_in_edit_mode:
                # --- Handle drag completion ---
                if self.is_sub_button and self.parent_folder:
                    if not self.drag_out_threshold_exceeded:
                        self.app.update_sub_button_order(self.parent_folder, dragged_sub_button=self, realtime=False)
                    else:
                        self.app.remove_sub_button_from_folder(self)
                    self.app.hide_blue_reorder_frame()
                    self.app.hide_red_removal_frame()
                else:  # Main button drag completion
                    if self.app.frame_visible and self.app.is_button_in_frame(self):
                        self.app.merge_folders()
                    self.app.finalize_button_order()
                    self.app.hide_frame()

                if not self.is_sub_button:  # After main button drag
                    if hasattr(self.app, 'expand_all_folders'):
                        self.app.expand_all_folders()

                if hasattr(self.app, 'controller') and hasattr(self.app.controller, 'save_current_layout'):
                    self.app.controller.save_current_layout()

                self.setDown(False)  # Reset visual pressed state
                self.update()
                return  # IMPORTANT: Do not fall through to super for drag operations

            # --- Handle click (not a drag, or not in edit mode drag) ---
            # A click is defined as press and release inside the button without significant movement.
            # QPushButton's default mouseReleaseEvent implementation handles emitting 'clicked()'
            # if the release is within bounds.
            else:
                # If it's a "new button", let the controller handle its specific click.
                # For other buttons, the controller also connects the `clicked` signal.
                # So, allowing super.mouseReleaseEvent() should be correct for all click types.
                if self.rect().contains(event.position().toPoint()):  # Ensure release is inside
                    super().mouseReleaseEvent(event)  # This emits clicked()
                else:  # Released outside, don't emit clicked, just reset state
                    self.setDown(False)
                    self.update()

        else:  # Not a left button release
            super().mouseReleaseEvent(event)

        # General cleanup for any release scenario if not returned earlier
        self.setDown(False)
        self.update()

    def _start_press_effect(self):
        self._suppress_dark = False
        self.fadeOpacity = 1.0
        if self._fade_anim and self._fade_anim.state() == QPropertyAnimation.Running:
            self._fade_anim.stop()
        if self._long_press_timer: self._long_press_timer.stop()

        self._long_press_timer = QTimer(self)
        self._long_press_timer.setSingleShot(True)
        self._long_press_timer.timeout.connect(self._disable_darkening_after_delay)
        self._long_press_timer.start(100)

    def _end_press_effect(self):
        if self._long_press_timer: self._long_press_timer.stop()
        if not self._suppress_dark and self.fadeOpacity > 0.01:
            if self._fade_anim and self._fade_anim.state() == QPropertyAnimation.Running:
                self._fade_anim.stop()

            self._fade_anim = QPropertyAnimation(self, b"fadeOpacity")
            self._fade_anim.setDuration(150)
            self._fade_anim.setEasingCurve(QEasingCurve.OutQuad)
            self._fade_anim.setStartValue(self.fadeOpacity)
            self._fade_anim.setEndValue(0.0)
            self._fade_anim.finished.connect(lambda: setattr(self, '_suppress_dark', True))
            self._fade_anim.start()
        else:
            self.fadeOpacity = 0.0
            self._suppress_dark = True

    def _disable_darkening_after_delay(self):
        if self.isDown():
            if self._fade_anim and self._fade_anim.state() == QPropertyAnimation.Running:
                self._fade_anim.stop()

            self._fade_anim = QPropertyAnimation(self, b"fadeOpacity")
            self._fade_anim.setDuration(180)
            self._fade_anim.setEasingCurve(QEasingCurve.OutQuad)
            self._fade_anim.setStartValue(self.fadeOpacity)
            self._fade_anim.setEndValue(0.0)
            self._fade_anim.finished.connect(lambda: setattr(self, '_suppress_dark', True))
            self._fade_anim.start()

    @Property(float)
    def fadeOpacity(self) -> float:
        return self._fade_opacity

    @fadeOpacity.setter
    def fadeOpacity(self, value: float):
        self._fade_opacity = value
        self.update()

    def _stop_recenter_timer(self):
        if hasattr(self, "_recenter_timer") and self._recenter_timer:
            if self._recenter_timer.isActive():
                self._recenter_timer.stop()
            self._recenter_timer.deleteLater()
            self._recenter_timer = None
# WordBookButton.py结束