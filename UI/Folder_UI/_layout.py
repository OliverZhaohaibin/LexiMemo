from PySide6.QtCore import QPoint, QRect


def calculate_main_button_positions(buttons, button_width, button_height, spacing, central_widget_width):
    """
    计算主界面按钮的位置
    
    Args:
        buttons: 按钮列表
        button_width: 按钮宽度
        button_height: 按钮高度
        spacing: 间距
        central_widget_width: 中央部件宽度
        
    Returns:
        按钮位置列表
    """
    target_positions = []
    current_x = spacing
    current_y = spacing + 40  # 留出编辑按钮的空间
    buttons_per_row = max(1, (central_widget_width - spacing) // (button_width + spacing))
    
    for i in range(len([btn for btn in buttons if not btn.is_sub_button])):
        if current_x + button_width > central_widget_width - spacing:
            current_y += button_height + spacing
            current_x = spacing
        target_positions.append(QPoint(current_x, current_y))
        current_x += button_width + spacing
        
    return target_positions


def calculate_sub_button_positions(folder_button, button_width, button_height, spacing, central_widget_width, folder_extra_width):
    """
    计算文件夹内子按钮的位置
    """
    target_positions = []
    # 删除folder_spacing,直接使用spacing
    current_y = folder_button.y() + button_height + spacing
    available_width = central_widget_width - spacing * 2 + folder_extra_width
    buttons_per_row = max(1, available_width // (button_width + spacing))
    rows = (len(folder_button.sub_buttons) + buttons_per_row - 1) // buttons_per_row
    
    for row in range(rows):
        for col in range(buttons_per_row):
            if len(target_positions) < len(folder_button.sub_buttons):
                # 使用统一的spacing
                x = spacing + col * (button_width + spacing)
                y = current_y + row * (button_height + spacing)
                target_positions.append(QPoint(x, y))
                
    return target_positions


def calculate_folder_area(folder_button, sub_buttons, button_width, button_height):
    """
    计算文件夹区域（包括文件夹按钮和所有子按钮）
    
    Args:
        folder_button: 文件夹按钮
        sub_buttons: 子按钮列表
        button_width: 按钮宽度
        button_height: 按钮高度
        
    Returns:
        文件夹区域的左上角坐标和右下角坐标
    """
    min_x = folder_button.x()
    min_y = folder_button.y()
    max_x = folder_button.x() + button_width
    max_y = folder_button.y() + button_height
    
    for sub_btn in sub_buttons:
        min_x = min(min_x, sub_btn.x())
        min_y = min(min_y, sub_btn.y())
        max_x = max(max_x, sub_btn.x() + button_width)
        max_y = max(max_y, sub_btn.y() + button_height)
        
    return min_x, min_y, max_x, max_y


def calculate_reorder_area(folder_button, button_width, button_height, spacing, central_widget_width, folder_extra_width):
    """
    计算文件夹内重排序区域

    Args:
        folder_button: 文件夹按钮
        button_width: 按钮宽度
        button_height: 按钮高度
        spacing: 间距
        central_widget_width: 中央部件宽度
        folder_extra_width: 文件夹额外宽度

    Returns:
        重排序区域
    """
    folder_spacing = spacing * 1.5
    available_width = central_widget_width - folder_spacing * 1.5 + folder_extra_width
    buttons_per_row = max(1, available_width // (button_width + folder_spacing))
    rows = (len(folder_button.sub_buttons) + buttons_per_row - 1) // buttons_per_row

    left = 0  # ✅ 左边界固定为0，不跟随按钮
    top = folder_button.y() + button_height
    width = central_widget_width  # ✅ 全宽
    height = (rows * (button_height + folder_spacing)) + folder_spacing * 1.01

    return QRect(left, top, width, height)

class FolderLayoutMixin:
    """为任意 QWidget 子类提供布局计算工具的无状态混入。"""

    # 直接把函数挂成静态方法，避免重复实现
    calculate_main_button_positions = staticmethod(calculate_main_button_positions)
    calculate_sub_button_positions  = staticmethod(calculate_sub_button_positions)
    calculate_folder_area           = staticmethod(calculate_folder_area)
    calculate_reorder_area          = staticmethod(calculate_reorder_area)


__all__ = [
    "FolderLayoutMixin",
    "calculate_main_button_positions",
    "calculate_sub_button_positions",
    "calculate_folder_area",
    "calculate_reorder_area",
]