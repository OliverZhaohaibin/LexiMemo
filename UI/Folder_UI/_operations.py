from .button import DraggableButton



def merge_buttons_to_folder(btn1, btn2, central_widget, app):
    """
    将两个按钮合并为一个文件夹
    
    Args:
        btn1: 第一个按钮
        btn2: 第二个按钮
        central_widget: 中央部件
        app: 应用程序实例
        
    Returns:
        创建的文件夹按钮
    """
    folder_name = f"Folder {len([b for b in app.buttons if b.is_folder]) + 1}"
    folder_button = DraggableButton(folder_name, central_widget, app)
    folder_button.is_folder = True
    folder_button.move(btn1.pos())
    folder_button.setStyleSheet("background-color: #f0f0f0; font-weight: bold;")
    
    # 将原按钮作为子按钮加入文件夹
    if btn1.is_folder:
        folder_button.sub_buttons.extend(btn1.sub_buttons)
    else:
        sub_btn1 = DraggableButton(btn1.text(), central_widget, app)
        sub_btn1.is_sub_button = True
        sub_btn1.parent_folder = folder_button
        folder_button.sub_buttons.append(sub_btn1)
        sub_btn1.hide()
        
    if btn2.is_folder:
        folder_button.sub_buttons.extend(btn2.sub_buttons)
    else:
        sub_btn2 = DraggableButton(btn2.text(), central_widget, app)
        sub_btn2.is_sub_button = True
        sub_btn2.parent_folder = folder_button
        folder_button.sub_buttons.append(sub_btn2)
        sub_btn2.hide()
        
    return folder_button


def add_button_to_folder(button_to_add, folder, central_widget, app):
    """
    将按钮添加到现有文件夹
    
    Args:
        button_to_add: 要添加的按钮
        folder: 目标文件夹
        central_widget: 中央部件
        app: 应用程序实例
        
    Returns:
        创建的子按钮
    """
    sub_btn = DraggableButton(button_to_add.text(), central_widget, app)
    sub_btn.is_sub_button = True
    sub_btn.parent_folder = folder
    folder.sub_buttons.append(sub_btn)
    sub_btn.hide()  # 初始隐藏
    
    return sub_btn


def remove_sub_button_from_folder(sub_btn, buttons_list):
    """
    从文件夹中移除子按钮
    
    Args:
        sub_btn: 要移除的子按钮
        buttons_list: 主按钮列表
    """
    parent_folder = sub_btn.parent_folder
    if parent_folder:
        if sub_btn in parent_folder.sub_buttons:
            parent_folder.sub_buttons.remove(sub_btn)
        if sub_btn not in buttons_list:
            buttons_list.append(sub_btn)
        sub_btn.is_sub_button = False
        sub_btn.parent_folder = None
        sub_btn.show()
        
        return parent_folder
    return None


def check_and_remove_folder_if_needed(folder_btn, buttons_list):
    """
    检查并在需要时移除文件夹（当文件夹内按钮少于2个时）
    
    Args:
        folder_btn: 文件夹按钮
        buttons_list: 主按钮列表
        
    Returns:
        bool: 是否移除了文件夹
    """
    if len(folder_btn.sub_buttons) < 2:
        print(f"文件夹 {folder_btn.text()} 内按钮不足2个，执行删除文件夹操作")
        if folder_btn in buttons_list:
            buttons_list.remove(folder_btn)
        if len(folder_btn.sub_buttons) == 1:
            remaining_btn = folder_btn.sub_buttons[0]
            remaining_btn.is_sub_button = False
            remaining_btn.parent_folder = None
            if remaining_btn not in buttons_list:
                buttons_list.append(remaining_btn)
        
        # 移除文件夹背景框
        if hasattr(folder_btn, 'background_frame'):
            folder_btn.background_frame.hide()
            folder_btn.background_frame.deleteLater()
            
        folder_btn.hide()
        return True
    return False
class FolderOperationMixin:
    """封装文件夹增删改操作的工具混入。"""

    merge_buttons_to_folder          = staticmethod(merge_buttons_to_folder)
    add_button_to_folder             = staticmethod(add_button_to_folder)
    remove_sub_button_from_folder    = staticmethod(remove_sub_button_from_folder)
    check_and_remove_folder_if_needed = staticmethod(check_and_remove_folder_if_needed)


__all__ = [
    "FolderOperationMixin",
    "merge_buttons_to_folder",
    "add_button_to_folder",
    "remove_sub_button_from_folder",
    "check_and_remove_folder_if_needed",
]
