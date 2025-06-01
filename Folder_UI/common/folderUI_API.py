from __future__ import annotations

from WordBookButton import WordBookButton
from PySide6.QtCore import QPoint, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup,QRect
from PySide6.QtWidgets import QGraphicsOpacityEffect
from typing import Dict


from Folder_UI.layout import (
    calculate_main_button_positions,
    calculate_sub_button_positions,
    calculate_folder_area
)

from Folder_UI.folder_background import (
    update_folder_background,
    FolderBackground,
    update_all_folder_backgrounds,
)

from Folder_UI.animations import (
    create_folder_toggle_animation,
    create_button_position_animation,
)
from Folder_UI.folder_operations import (
    add_button_to_folder,
    remove_sub_button_from_folder as _remove_sub_btn,
    check_and_remove_folder_if_needed,
)





"""Folder Operation Mixin

负责『文件夹的业务级操作』—— 合并按钮、将按钮加入文件夹、从文件夹拖出子按钮。
与动画 / 布局 / 提示框逻辑解耦，只在操作结束后调用
    • self.update_button_positions()
    • self.toggle_folder(...)
等宿主暴露的接口。
"""


class FolderOperationMixin:
    """业务操作 Mixin。需要宿主类提供：
        buttons, new_book_button, scroll_content
        button_width / button_height / spacing / folder_extra_width
        edit_mode, proximity_pair, frame_visible
        update_button_positions(), toggle_folder(folder_btn)
        hide_frame()  (来自 FolderHintMixin)
    """

    # ------------------------------------------------------------------
    # 将子按钮拖出文件夹
    # ------------------------------------------------------------------
    def remove_sub_button_from_folder(self, sub_btn):
        parent_folder = _remove_sub_btn(sub_btn, self.buttons)
        if not parent_folder:
            return

        # 删掉旧 WordBookButton/DraggableButton 引用
        try:
            parent_folder.sub_buttons.remove(sub_btn)
        except ValueError:
            pass

        # 作为主按钮加入 self.buttons
        if sub_btn not in self.buttons:
            self.buttons.append(sub_btn)
        sub_btn.is_sub_button = False
        sub_btn.parent_folder = None
        sub_btn.show()

        if self.edit_mode:
            sub_btn.start_jitter()

        self.update_button_positions()
        # ⭐️ 子按钮拖出后刷新文件夹图标
        if parent_folder and parent_folder.is_folder:
            parent_folder.update_folder_icon()

        self.update_button_positions()
        # 如果文件夹子数不足 2 则解散
        if check_and_remove_folder_if_needed(parent_folder, self.buttons):
            parent_folder.setParent(None)
            parent_folder.deleteLater()

        self.update_button_positions()

    # ------------------------------------------------------------------
    # 根据 self.proximity_pair 合并 / 创建文件夹
    # ------------------------------------------------------------------
    def merge_folders(self):
        if not getattr(self, "proximity_pair", None):
            return

        btn1, btn2 = self.proximity_pair

        # ---------- A. 普通按钮拖到已有文件夹 ---------- #
        if btn2.is_folder and not btn1.is_folder:
            self._add_to_existing_folder(src_btn=btn1, folder_btn=btn2)

        elif btn1.is_folder and not btn2.is_folder:
            self._add_to_existing_folder(src_btn=btn2, folder_btn=btn1)

        # ---------- B. 两个普通按钮 → 新文件夹 ---------- #
        elif not btn1.is_folder and not btn2.is_folder:
            self._create_new_folder(btn1, btn2)

        # ---------- 完成 ---------- #
        self.update_button_positions()
        self.hide_frame()

    # ============================================================
    # 内部工具
    # ============================================================
    def _add_to_existing_folder(self, src_btn, folder_btn):
        """把普通按钮 src_btn 加入已存在的 folder_btn 里，并确保子按钮能正常打开单词册。"""
        import os, sys

        # ① 先用旧 helper 造一个占位 DraggableButton（保持原逻辑，便于动画）
        placeholder = add_button_to_folder(src_btn, folder_btn, self.scroll_content, self)
        folder_btn.sub_buttons.remove(placeholder)
        placeholder.setParent(None)
        placeholder.deleteLater()

        # ② 创建真正的 WordBookButton 子按钮
        color = getattr(src_btn, "color", "#f0f0f0")
        new_sub = WordBookButton(src_btn.text(), color, parent=self.scroll_content, app=self)
        new_sub.is_sub_button = True
        new_sub.parent_folder = folder_btn
        new_sub.hide()
        folder_btn.sub_buttons.append(new_sub)

        # ③ 绑定点击事件 —— 解决 **文件夹内按钮无法打开单词册** 的 Bug
        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        books_dir = os.path.join(base_dir, "books")
        folder_name = f"books_{new_sub.text()}_{new_sub.color}"
        book_path = os.path.join(books_dir, folder_name)
        new_sub.clicked.connect(lambda _, p=book_path: self.show_word_book(p))

        # ④ 将原按钮从主按钮列表移除并隐藏
        if src_btn in self.buttons:
            self.buttons.remove(src_btn)
        src_btn.hide()

        # ⑤ 视觉 & 状态处理
        if self.edit_mode:
            new_sub.start_jitter()
            
        # ⑥ 绑定右键菜单
        if hasattr(self, 'bind_delete_context'):
            self.bind_delete_context()

        if not folder_btn.is_expanded and self.edit_mode:
            self.toggle_folder(folder_btn)          # 编辑模式下自动展开
        elif folder_btn.is_expanded:
            self.update_button_positions()
        else:
            self.update_button_positions()

        # ⭐️ 生成 / 刷新文件夹九宫格图标
        folder_btn.update_folder_icon()

    def _create_new_folder(self, btn1, btn2):
        """btn1 与 btn2 均为普通按钮时，生成新的文件夹按钮，并给子按钮加上点击事件。"""
        import os, sys

        folder_name = f"Folder {len([b for b in self.buttons if getattr(b, 'is_folder', False)]) + 1}"
        folder_color = getattr(btn1, "color", "#f0f0f0")
        folder_btn = WordBookButton(folder_name, folder_color, parent=self.scroll_content, app=self)
        folder_btn.is_folder = True
        folder_btn.is_expanded = False
        folder_btn.move(btn1.pos())

        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        books_dir = os.path.join(base_dir, "books")

        # —— 把 btn1 / btn2 变成子按钮 —— #
        for src in (btn1, btn2):
            color = getattr(src, "color", "#f0f0f0")
            new_sub = WordBookButton(src.text(), color, parent=self.scroll_content, app=self)
            new_sub.is_sub_button = True
            new_sub.parent_folder = folder_btn
            new_sub.hide()
            folder_btn.sub_buttons.append(new_sub)

            # 点击事件
            folder_name_path = f"books_{new_sub.text()}_{new_sub.color}"
            book_path = os.path.join(books_dir, folder_name_path)
            new_sub.clicked.connect(lambda _, p=book_path: self.show_word_book(p))

            if src in self.buttons:
                self.buttons.remove(src)
            src.hide()

        # ⭐️ 生成九宫格图标
        folder_btn.update_folder_icon()

        # —— 注册并展开 —— #
        self.buttons.append(folder_btn)
        folder_btn.show()
        self.toggle_folder(folder_btn)

        if self.edit_mode:
            folder_btn.start_jitter()
            for s in folder_btn.sub_buttons:
                s.start_jitter()
                
        # 绑定右键菜单
        if hasattr(self, 'bind_delete_context'):
            self.bind_delete_context()


"""Folder Animation Mixin

抽离 cover.py / app.py 等处 *文件夹相关动画* 逻辑：
    • toggle_folder  —— 展开 / 折叠（主动画）
    • collapse_all_folders / expand_all_folders —— 一键折叠 / 恢复

宿主（通常是一个主窗口类，如 WordAppCover）必须提供：
    buttons:                 list[Button]      — 主界面所有按钮
    new_book_button:         Button            — "新建单词册" 按钮
    scroll_content / scroll_area               — 用于获取宽度
    button_width / button_height / spacing     — 尺寸参数
    update_button_positions()                  — 刷新整体布局

其余属性（folder_expanded_states / all_folders_collapsed）会在 Mixin 内自动维护。
"""

class FolderAnimationMixin:
    """混入类：提供文件夹展开 / 折叠相关全部动画 & 批量折叠/恢复能力。"""

    # ------------------------------------------------------------
    # 公共 API
    # ------------------------------------------------------------
    def toggle_folder(self, folder_button):
        """切换单个文件夹的展开 / 折叠状态（含动画）。"""
        if not getattr(folder_button, "is_folder", False):
            return

        running = getattr(folder_button, "folder_animation_group", None)
        if running and running.state() == QParallelAnimationGroup.Running:
            return

        is_expanding = not folder_button.is_expanded
        folder_button.is_expanded = is_expanding

        # ---------- 准备背景框 ----------
        self._ensure_background_frames(folder_button)

        # 展开前需显示子按钮
        if is_expanding:
            for sub in folder_button.sub_buttons:
                sub.show()

        # ---------- 计算所有按钮最终位置 ----------
        final_pos, new_book_target = self._calculate_final_positions(folder_button, is_expanding)

        # ---------- (1) 子按钮动画 ----------
        sub_targets = [final_pos[s] for s in folder_button.sub_buttons if s in final_pos]
        folder_toggle_anim = create_folder_toggle_animation(
            folder_button, sub_targets, self.button_width, self.button_height, self.spacing
        )

        # ---------- (2) 背景框动画 ----------
        bg_geom_anim, bg_opacity_anim = self._build_background_anims(
            folder_button, sub_targets, is_expanding
        )

        # ---------- (3) 其他按钮 & 新建按钮动画 ----------
        move_group = self._build_move_group(folder_button, final_pos, new_book_target)

        # ---------- (4) 其他已展开文件夹背景框几何动画 ----------
        other_bg_anims = self._build_other_bg_group(folder_button, final_pos)

        # ---------- 汇总启动 ----------
        master = QParallelAnimationGroup()
        for g in (
            folder_toggle_anim,
            bg_geom_anim,
            bg_opacity_anim,
            move_group,
            other_bg_anims,
        ):
            master.addAnimation(g)

        master.finished.connect(lambda: self._post_folder_animation(folder_button))
        folder_button.folder_animation_group = master
        master.start()

    def collapse_all_folders(self):
        """批量折叠界面上 *所有* 已展开文件夹（并记录状态）。"""
        # 清空旧记录
        self.folder_expanded_states: Dict = {}

        for btn in self.buttons:
            if btn.is_folder and btn.is_expanded:
                self.folder_expanded_states[btn] = True

                # 若未在动画中，创建折叠动画
                if not getattr(btn, "folder_animation_group", None) or btn.folder_animation_group.state() != QParallelAnimationGroup.Running:
                    btn.is_expanded = False  # 改状态
                    sub_pos = [sub_btn.pos() for sub_btn in btn.sub_buttons]
                    anim = create_folder_toggle_animation(
                        btn,
                        sub_pos,
                        self.button_width,
                        self.button_height,
                        self.spacing,
                    )
                    anim.finished.connect(lambda b=btn: self._post_folder_animation(b))
                    btn.folder_animation_group = anim
                    anim.start()

        self.all_folders_collapsed = True

    def expand_all_folders(self):
        """恢复上一次 `collapse_all_folders` 保存的展开状态。"""
        if not getattr(self, "all_folders_collapsed", False):
            return

        for btn, was_expanded in getattr(self, "folder_expanded_states", {}).items():
            if was_expanded and not btn.is_expanded:
                if not getattr(btn, "folder_animation_group", None) or btn.folder_animation_group.state() != QParallelAnimationGroup.Running:
                    btn.is_expanded = True
                    # 显示子按钮以便动画可见
                    for sub in btn.sub_buttons:
                        sub.show()
                    target_positions = self._sub_targets(btn)
                    anim = create_folder_toggle_animation(
                        btn,
                        target_positions,
                        self.button_width,
                        self.button_height,
                        self.spacing,
                    )
                    btn.folder_animation_group = anim
                    anim.start()

        # 清空记录
        self.folder_expanded_states.clear()
        self.all_folders_collapsed = False
        # 最后刷新布局
        self.update_button_positions()

    # ------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------
    def _ensure_background_frames(self, folder_button):
        """确保所有展开文件夹都拥有可见背景框。"""
        for btn in self.buttons:
            if btn.is_folder and (btn.is_expanded or btn is folder_button):
                if not hasattr(btn, "background_frame"):
                    btn.background_frame = FolderBackground(self.scroll_content)
                    eff = QGraphicsOpacityEffect(btn.background_frame)
                    eff.setOpacity(1.0)
                    btn.background_frame.setGraphicsEffect(eff)
                btn.background_frame.lower()
                btn.background_frame.show()

    # ---- 位置计算 ----
    def _calculate_final_positions(self, folder_button, is_expanding):
        bw, bh, sp = self.button_width, self.button_height, self.spacing
        avail_w = self.scroll_content.width() or self.scroll_area.viewport().width()
        x, y = sp, sp + 40
        final_pos: Dict = {}

        for btn in self.buttons:
            if x + bw > avail_w - sp:
                y += bh + sp
                x = sp
            final_pos[btn] = QPoint(x, y)
            if btn.is_folder and (
                btn.is_expanded or (btn is folder_button and is_expanding)
            ):
                y += bh + sp
                x = sp
                fsp = sp * 1.5
                per_row = max(1, int((avail_w - fsp * 2) // (bw + fsp)))
                for idx, sub in enumerate(btn.sub_buttons):
                    if idx and idx % per_row == 0:
                        y += bh + fsp
                        x = sp
                    final_pos[sub] = QPoint(x, y)
                    x += bw + fsp
                if x != sp:
                    y += bh + sp
                    x = sp
            else:
                x += bw + sp

        if x + bw > avail_w - sp:
            y += bh + sp
            x = sp
        new_book_target = QPoint(x, y)
        return final_pos, new_book_target

    def _sub_targets(self, folder_button):
        """展开动画子按钮目标位置（用于 expand_all_folders）。"""
        final_pos, _ = self._calculate_final_positions(folder_button, True)
        return [final_pos[s] for s in folder_button.sub_buttons if s in final_pos]

    # ---- 背景框动画生成 ----
    def _build_background_anims(self, folder_button, sub_targets, is_expanding):
        bw, bh, sp = self.button_width, self.button_height, self.spacing

        def calc_rect(positions):
            if not positions:
                return folder_button.geometry()
            min_x = min(p.x() for p in positions)
            min_y = min(p.y() for p in positions)
            max_x = max(p.x() for p in positions) + bw
            max_y = max(p.y() for p in positions) + bh
            margin = sp // 2
            return QRect(min_x - margin, min_y - margin, max_x - min_x + margin * 2, max_y - min_y + margin * 2)

        bg_frame = folder_button.background_frame
        bg_eff = bg_frame.graphicsEffect()
        if is_expanding:
            bg_start, bg_end = folder_button.geometry(), calc_rect(sub_targets)
        else:
            bg_start, bg_end = bg_frame.geometry(), folder_button.geometry()

        geom = QPropertyAnimation(bg_frame, b"geometry")
        geom.setDuration(450)
        geom.setEasingCurve(QEasingCurve.OutBack if is_expanding else QEasingCurve.InBack)
        geom.setStartValue(bg_start)
        geom.setEndValue(bg_end)

        opac = QPropertyAnimation(bg_eff, b"opacity")
        opac.setDuration(450)
        if is_expanding:
            opac.setStartValue(0.0 if bg_eff.opacity() < 1e-3 else bg_eff.opacity())
            opac.setEndValue(1.0)
        else:
            opac.setStartValue(bg_eff.opacity())
            opac.setEndValue(0.0)
            opac.finished.connect(lambda: (bg_frame.hide(), bg_eff.setOpacity(1.0)))
        return geom, opac

    # ---- 其他按钮移动动画 ----
    def _build_move_group(self, folder_button, final_pos, new_book_target):
        group = QParallelAnimationGroup()
        for btn, tgt in final_pos.items():
            if btn not in folder_button.sub_buttons and btn is not folder_button and not getattr(btn, "is_dragging", False):
                group.addAnimation(create_button_position_animation(btn, tgt, 450))
        if self.new_book_button.pos() != new_book_target:
            group.addAnimation(create_button_position_animation(self.new_book_button, new_book_target, 450))
        return group

    # ---- 其他展开文件夹背景框几何动画 ----
    def _build_other_bg_group(self, folder_button, final_pos):
        group = QParallelAnimationGroup()
        bw, bh, sp = self.button_width, self.button_height, self.spacing

        def calc_rect(positions):
            if not positions:
                return QRect()
            min_x = min(p.x() for p in positions)
            min_y = min(p.y() for p in positions)
            max_x = max(p.x() for p in positions) + bw
            max_y = max(p.y() for p in positions) + bh
            margin = sp // 2
            return QRect(min_x - margin, min_y - margin, max_x - min_x + margin * 2, max_y - min_y + margin * 2)

        for btn in self.buttons:
            if btn.is_folder and btn.is_expanded and btn is not folder_button:
                tgt = calc_rect([final_pos[s] for s in btn.sub_buttons])
                if tgt != btn.background_frame.geometry():
                    anim = QPropertyAnimation(btn.background_frame, b"geometry")
                    anim.setDuration(450)
                    anim.setEasingCurve(QEasingCurve.OutBack)
                    anim.setStartValue(btn.background_frame.geometry())
                    anim.setEndValue(tgt)
                    group.addAnimation(anim)
        return group

    # ------------------------------------------------------------
    # 钩子
    # ------------------------------------------------------------
    def _post_folder_animation(self, folder_button):
        """动画结束后的统一收尾。"""
        self.update_button_positions()
        if not folder_button.is_expanded:
            for sub_btn in folder_button.sub_buttons:
                sub_btn.hide()
        update_folder_background(self, folder_button)





class FolderHintMixin:
    """统一管理『合并提示框 / 拖出提示红框 / 文件夹内部排序蓝框』的显示逻辑。

    宿主类需具备：
        • frame                 —— 蓝色合并提示 QFrame
        • blue_reorder_frame    —— 蓝色子排序区 QFrame
        • red_removal_frame     —— 红色移出提示 QFrame
        • frame_visible         —— bool 状态标记
        • button_width / button_height / spacing
        • scroll_content.width()  用于蓝框宽度
    """

    # ============================================================
    # 合并提示框（蓝色虚线框）
    # ============================================================
    def show_frame(self, btn1, btn2):
        """在 btn1 与 btn2 共同包围区域绘制蓝色合并提示框。"""
        left = min(btn1.x(), btn2.x()) - 10
        top = min(btn1.y(), btn2.y()) - 10
        right = max(btn1.x() + self.button_width, btn2.x() + self.button_width) + 10
        bottom = max(btn1.y() + self.button_height, btn2.y() + self.button_height) + 10
        self.frame.setGeometry(left, top, right - left, bottom - top)
        self.frame.show()
        self.frame_visible = True

    def hide_frame(self):
        self.frame.hide()
        self.frame_visible = False

    def is_button_in_frame(self, button):
        """检查给定按钮是否落在当前蓝色提示框内。"""
        if not self.frame_visible:
            return False
        button_rect = QRect(button.pos(), button.size())
        return self.frame.geometry().contains(button_rect.center())

    # ============================================================
    # 文件夹内部子按钮重排蓝框
    # ============================================================
    def show_blue_reorder_frame(self, parent_folder):
        """显示蓝框，标识文件夹内可拖拽排序区域（左边界固定为 0）。"""
        min_x, min_y, max_x, max_y = calculate_folder_area(
            parent_folder, parent_folder.sub_buttons, self.button_width, self.button_height
        )
        margin = 10
        left = 0
        top = min_y - margin
        height = max_y - min_y + 2 * margin
        self.blue_reorder_frame.setGeometry(0, top, self.scroll_content.width(), height)
        self.blue_reorder_frame.show()

    def hide_blue_reorder_frame(self):
        self.blue_reorder_frame.hide()

    # ============================================================
    # 拖出文件夹红框
    # ============================================================
    def show_red_removal_frame(self, parent_folder):
        min_x, min_y, max_x, max_y = calculate_folder_area(
            parent_folder, parent_folder.sub_buttons, self.button_width, self.button_height
        )
        margin = 10
        left = min_x - margin
        top = min_y - margin
        width = max_x - min_x + 2 * margin
        height = max_y - min_y + 2 * margin
        self.red_removal_frame.setGeometry(left, top, width, height)
        self.red_removal_frame.show()

    def hide_red_removal_frame(self):
        self.red_removal_frame.hide()




class FolderLayoutMixin:
    """
    把『按钮网格布局 / 拖拽排序』相关算法统一放到这里。

    ⚙️ 依赖宿主类属性
    -----------------
        buttons                    主按钮列表（含文件夹按钮）
        new_book_button            “新建单词册”按钮
        scroll_content / scroll_area
        button_width / button_height / spacing
        folder_extra_width         文件夹内部行列计算时的额外宽度
        frame_visible              标识合并提示框当前是否可见
        show_frame / hide_frame
        show_blue_reorder_frame / hide_blue_reorder_frame
        show_red_removal_frame / hide_red_removal_frame
    """

    # ============================================================
    # 主按钮 / “新建单词册” 按位置刷新
    # ============================================================
    def update_button_positions(self):
        """
        实时重新计算所有主按钮 & 子按钮位置。
        与窗口大小或按钮数量变化、拖拽移动等事件绑定。
        """
        if not getattr(self, "buttons", None):
            return

        available_width = self.scroll_content.width() or self.scroll_area.viewport().width()
        bw, bh, sp = self.button_width, self.button_height, self.spacing

        button_width_with_spacing = bw + sp
        self.buttons_per_row = max(1, (available_width - sp) // button_width_with_spacing)

        start_x, start_y = sp, sp + 40
        current_x, current_y = start_x, start_y

        for btn in self.buttons:
            if getattr(btn, "is_dragging", False):
                continue

            # —— 主按钮位置 —— #
            if current_x + bw > available_width - sp:
                current_y += bh + sp
                current_x = start_x
            btn.move(current_x, current_y)

            # —— 展开文件夹：子按钮独占若干行 —— #
            if btn.is_folder and btn.is_expanded:
                current_y += bh + sp
                current_x = start_x

                fsp = sp * 1.5
                sub_per_row = max(1, int((available_width - fsp * 2) // (bw + fsp)))

                for idx, sub_btn in enumerate(btn.sub_buttons):
                    if getattr(self.new_book_button, "is_dragging", False):
                        continue

                    row, col = divmod(idx, sub_per_row)
                    sx = start_x + col * (bw + fsp)
                    sy = current_y + row * (bh + fsp)
                    sub_btn.move(sx, sy)
                    sub_btn.show()

                rows_cnt = (len(btn.sub_buttons) + sub_per_row - 1) // sub_per_row
                current_y += rows_cnt * (bh + fsp) + sp
                current_x = start_x

                update_folder_background(self, btn)
            else:
                current_x += button_width_with_spacing

        # —— 放置『新建单词册』按钮 —— #
        if current_x + bw > available_width - sp:
            current_y += bh + sp
            current_x = start_x
        self.new_book_button.move(current_x, current_y)

        # —— 更新滚动内容高度 —— #
        self.scroll_content.setMinimumHeight(current_y + bh + sp)

        # —— 刷新灰色背景框 —— #
        update_all_folder_backgrounds(self, bw, bh)

    # ============================================================
    # 主界面按钮拖拽时的实时排序
    # ============================================================
    def update_button_order(self, dragged_button):
        """拖动过程中：实时重排 + 记录原坐标 + 记录当前拖拽对象"""
        if dragged_button.is_sub_button:
            return

        # —— ① 首次拖动时缓存原始坐标 —— #
        if not hasattr(dragged_button, "_origin_pos"):
            dragged_button._origin_pos = dragged_button.pos()
        self._current_dragged_button = dragged_button

        # —— ② 计算重排 —— #
        others = [b for b in self.buttons if b is not dragged_button and not b.is_sub_button]
        targets = calculate_main_button_positions(
            self.buttons, self.button_width, self.button_height,
            self.spacing, self.scroll_content.width(),
        )
        if not targets:
            return

        insert_idx = min(
            range(len(targets)),
            key=lambda i: (targets[i] - dragged_button.pos()).manhattanLength(),
        )

        reordered, iter_others = [], iter(others)
        for i in range(len(targets) + 1):
            if i == insert_idx:
                reordered.append(dragged_button)
            else:
                try:
                    reordered.append(next(iter_others))
                except StopIteration:
                    pass

        main_buttons = [b for b in self.buttons if not b.is_sub_button]
        for b in reordered:
            if b in main_buttons:
                main_buttons.remove(b)
        main_buttons = reordered
        self.buttons = [b for b in self.buttons if b.is_sub_button] + main_buttons

        self.animate_button_positions(dragged_button)

    def animate_button_positions(self, dragged_button=None):
        """
        实时更新按钮位置，并让『新建单词册』按钮在排序时自动让位、
        始终保持在网格的最后一格（向前吸附）。
        """
        from PySide6.QtCore import QPoint

        # —— 1. 主按钮（不含子按钮） —— #
        targets = calculate_main_button_positions(
            self.buttons,
            self.button_width,
            self.button_height,
            self.spacing,
            self.scroll_content.width(),
        )
        main_buttons = [b for b in self.buttons if not b.is_sub_button]

        for i, btn in enumerate(main_buttons):
            if (
                i < len(targets)
                and btn is not dragged_button
                and not getattr(btn, "is_dragging", False)
            ):
                btn.move(targets[i])

        # —— 2. 计算并移动『新建单词册』按钮 —— #
        bw, bh, sp = self.button_width, self.button_height, self.spacing
        avail_w    = self.scroll_content.width() or self.scroll_area.viewport().width()
        x, y       = sp, sp + 40

        for btn in main_buttons:
            # 主按钮占位
            if x + bw > avail_w - sp:
                y += bh + sp
                x  = sp
            x += bw + sp

            # 若为展开文件夹，再加上子按钮行数
            if getattr(btn, "is_folder", False) and btn.is_expanded:
                y += bh + sp
                x  = sp
                fsp      = sp * 1.5
                per_row  = max(1, int((avail_w - fsp * 2) // (bw + fsp)))
                rows_cnt = (len(btn.sub_buttons) + per_row - 1) // per_row
                y += rows_cnt * (bh + fsp)

        if x + bw > avail_w - sp:
            y += bh + sp
            x  = sp
        new_target = QPoint(x, y)

        if getattr(self, "new_book_button", None) and self.new_book_button.pos() != new_target:
            self.new_book_button.move(new_target)

    def finalize_button_order(self):
        """
        松手后：播放 300 ms 吸附动画；若按钮仍处于非法位置，则回弹到 _origin_pos。
        """
        targets = calculate_main_button_positions(
            self.buttons, self.button_width, self.button_height,
            self.spacing, self.scroll_content.width(),
        )
        main_buttons = [b for b in self.buttons if not b.is_sub_button]

        anim_group = QParallelAnimationGroup()
        for i, btn in enumerate(main_buttons):
            if i < len(targets) and btn.pos() != targets[i]:
                anim = QPropertyAnimation(btn, b"pos")
                anim.setDuration(300)
                anim.setEasingCurve(QEasingCurve.OutBack)
                anim.setStartValue(btn.pos())
                anim.setEndValue(targets[i])
                anim_group.addAnimation(anim)

        # —— ③ 回弹检测 —— #
        dragged_btn = getattr(self, "_current_dragged_button", None)
        if dragged_btn is not None:
            try:
                tgt_idx  = main_buttons.index(dragged_btn)
                tgt_pos  = targets[tgt_idx]
            except ValueError:
                tgt_pos  = getattr(dragged_btn, "_origin_pos", dragged_btn.pos())

            if (dragged_btn.pos() - tgt_pos).manhattanLength() > 5:
                revert_anim = QPropertyAnimation(dragged_btn, b"pos")
                revert_anim.setDuration(250)
                revert_anim.setEasingCurve(QEasingCurve.OutBack)
                revert_anim.setStartValue(dragged_btn.pos())
                revert_anim.setEndValue(getattr(dragged_btn, "_origin_pos", tgt_pos))
                anim_group.addAnimation(revert_anim)

        anim_group.finished.connect(self.update_button_positions)
        anim_group.start()

    # ============================================================
    # 文件夹内子按钮排序
    # ============================================================
    def update_sub_button_order(self, folder_button, dragged_sub_button=None, realtime=False):
        """
        文件夹内子按钮排序

        Parameters
        ----------
        folder_button : WordBookButton  文件夹按钮
        dragged_sub_button : WordBookButton | None  当前正在拖动的子按钮
        realtime : bool
            • True  -> 拖动过程中，其他子按钮立即让位（无动画）
            • False -> 松手后，播放吸附动画到目标网格
        """
        # 计算各网格坐标
        targets = calculate_sub_button_positions(
            folder_button,
            self.button_width,
            self.button_height,
            self.spacing,
            self.scroll_content.width(),
            self.folder_extra_width,
        )

        # ---------- 重排 folder_button.sub_buttons 顺序 ----------
        if dragged_sub_button is not None:
            # 找到离「拖动中心」最近的网格索引
            d_center = QPoint(
                dragged_sub_button.x() + self.button_width // 2,
                dragged_sub_button.y() + self.button_height // 2,
            )
            closest_idx = min(
                range(len(targets)),
                key=lambda i: (
                    targets[i] + QPoint(self.button_width // 2, self.button_height // 2) - d_center
                ).manhattanLength(),
            )

            # 生成新的子按钮顺序
            others = [b for b in folder_button.sub_buttons if b is not dragged_sub_button]
            new_order = []
            it = iter(others)
            for idx in range(len(folder_button.sub_buttons)):
                new_order.append(dragged_sub_button if idx == closest_idx else next(it, None))
            folder_button.sub_buttons = new_order

        # ---------- 位置处理 ----------
        if realtime:
            # 拖动中：立即移动其余子按钮（无动画），保持跟随
            self.finalize_sub_button_order_realtime(folder_button, dragged_button=dragged_sub_button)
        else:
            # 松手：播放 300 ms 吸附动画
            self.finalize_sub_button_order(folder_button, dragged_button=dragged_sub_button)

    def finalize_sub_button_order_realtime(self, folder_button, dragged_button=None):
        """
        拖动过程中实时刷新子按钮位置（无动画），并同步更新灰色背景框。
        """
        targets = calculate_sub_button_positions(
            folder_button,
            self.button_width,
            self.button_height,
            self.spacing,
            self.scroll_content.width(),
            self.folder_extra_width,
        )

        for i, btn in enumerate(folder_button.sub_buttons):
            if (
                i < len(targets)
                and btn is not dragged_button
                and not getattr(btn, "is_dragging", False)
            ):
                btn.move(targets[i])

        # 拖动时实时调整文件夹灰色背景框
        update_folder_background(self, folder_button)

    def finalize_sub_button_order(self, folder_button, dragged_button=None):
        targets = calculate_sub_button_positions(
            folder_button,
            self.button_width,
            self.button_height,
            self.spacing,
            self.scroll_content.width(),
            self.folder_extra_width,
        )

        anim_group = QParallelAnimationGroup()
        for i, btn in enumerate(folder_button.sub_buttons):
            if (
                i < len(targets)
                and btn is not dragged_button
                and not getattr(btn, "is_dragging", False)
                and btn.pos() != targets[i]
            ):
                anim = QPropertyAnimation(btn, b"pos")
                anim.setDuration(300)
                anim.setEasingCurve(QEasingCurve.OutBack)
                anim.setStartValue(btn.pos())
                anim.setEndValue(targets[i])
                anim_group.addAnimation(anim)

        anim_group.finished.connect(lambda: update_folder_background(self, folder_button))
        anim_group.start()
