"""该模块处理鼠标输入。覆盖拖拽、右键菜单与释放收尾逻辑。"""

from PySide6.QtCore import Qt


def handle_mouse_press(pet, event) -> bool:
    """处理鼠标按下。左键进入拖拽，右键弹出菜单。"""
    if event.button() == Qt.MouseButton.LeftButton:
        # 左键按下即进入拖拽。同时切换拖拽动画。
        pet.state.begin_drag()
        pet.drag_offset = event.globalPosition().toPoint() - pet.pos()
        pet.set_drag_animation()
        event.accept()
        return True

    if event.button() == Qt.MouseButton.RightButton:
        # 右键弹出菜单。菜单锚点取鼠标全局坐标。
        pet.show_context_menu(event.globalPosition().toPoint())
        event.accept()
        return True

    return False


def handle_mouse_move(pet, event) -> bool:
    """处理鼠标移动。仅在拖拽状态下同步移动窗口。"""
    if not pet.state.is_dragging:
        return False

    # 按偏移量计算新位置。鼠标全局坐标减去按下时偏移量。
    new_pos = event.globalPosition().toPoint() - pet.drag_offset
    pet.move(new_pos)
    pet.movement.constrain_to_screen()
    event.accept()
    return True


def handle_mouse_release(pet, event) -> bool:
    """处理鼠标释放。结束拖拽并恢复后续状态。"""
    if event.button() != Qt.MouseButton.LeftButton or not pet.state.is_dragging:
        return False

    # 释放后尝试进入休息。失败时恢复当前状态对应动画。
    pet.state.end_drag()
    pet.idle.try_enter_rest()
    if not pet.state.in_rest:
        pet._apply_state_animation()

    event.accept()
    return True
