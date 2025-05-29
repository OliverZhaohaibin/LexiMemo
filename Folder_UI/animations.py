from PySide6.QtCore import QPropertyAnimation, QParallelAnimationGroup, QEasingCurve, QPoint


def create_folder_toggle_animation(folder_button, target_positions, button_width, button_height, spacing):
    """
    创建文件夹展开/关闭的动画

    Args:
        folder_button: 文件夹按钮
        target_positions: 子按钮目标位置列表
        button_width: 按钮宽度
        button_height: 按钮高度
        spacing: 间距

    Returns:
        动画组
    """
    master_anim_group = QParallelAnimationGroup()

    # folder_button.is_expanded 是「目标状态」：
    # True  ➜ 正在展开；False ➜ 正在折叠
    is_expanding = folder_button.is_expanded
    duration_base = 450 if is_expanding else 250  # 折叠更快
    duration_increment = 100 if is_expanding else 40  # 折叠更快

    for index, sub_btn in enumerate(folder_button.sub_buttons):
        if is_expanding:
            # 展开：从文件夹中心移动到目标网格
            sub_btn.show()
            sub_btn.setWindowOpacity(0)
            start_pos = folder_button.pos()
            end_pos = target_positions[index]
        else:
            # 折叠：从当前网格回收至文件夹中心
            start_pos = sub_btn.pos()
            end_pos = folder_button.pos()

        # 位置动画
        pos_anim = QPropertyAnimation(sub_btn, b"pos")
        pos_anim.setDuration(duration_base + index * duration_increment)
        pos_anim.setStartValue(start_pos)
        pos_anim.setEndValue(end_pos)
        pos_anim.setEasingCurve(QEasingCurve.OutBack if is_expanding
                                else QEasingCurve.InBack)
        master_anim_group.addAnimation(pos_anim)

        # 透明度动画
        opacity_anim = QPropertyAnimation(sub_btn, b"windowOpacity")
        opacity_anim.setDuration(duration_base - 50)
        opacity_anim.setStartValue(0 if is_expanding else 1)
        opacity_anim.setEndValue(1 if is_expanding else 0)
        opacity_anim.setEasingCurve(QEasingCurve.InOutQuad)
        master_anim_group.addAnimation(opacity_anim)

        # 折叠结束后隐藏子按钮
        if not is_expanding:
            pos_anim.finished.connect(sub_btn.hide)

    # 动画结束后统一刷新布局
    if folder_button.app:
        master_anim_group.finished.connect(
            folder_button.app.update_button_positions
        )

    return master_anim_group


def create_button_position_animation(button, target_pos, duration=200, easing_curve=QEasingCurve.OutBack):
    """
    创建按钮位置动画
    
    Args:
        button: 按钮
        target_pos: 目标位置
        duration: 动画时长
        easing_curve: 缓动曲线
        
    Returns:
        位置动画
    """
    animation = QPropertyAnimation(button, b"pos")
    animation.setDuration(duration)
    animation.setStartValue(button.pos())
    animation.setEndValue(target_pos)
    animation.setEasingCurve(easing_curve)
    return animation