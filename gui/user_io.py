import json
from PyQt5.QtWidgets import QFileDialog, QMessageBox

def export_users_dialog(user_manager, parent, selected_names=None):
    path, _ = QFileDialog.getSaveFileName(parent, "导出用户", "users_export.json", "JSON Files (*.json)")
    if not path:
        return
    try:
        users = user_manager.get_all_users()
        if selected_names is not None:
            users = {k: v for k, v in users.items() if k in selected_names}
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        QMessageBox.information(parent, "导出成功", f"用户信息已导出到: {path}")
    except Exception as e:
        QMessageBox.critical(parent, "导出失败", str(e))

def import_users_dialog(user_manager, parent):
    path, _ = QFileDialog.getOpenFileName(parent, "导入用户", "", "JSON Files (*.json)")
    if not path:
        return
    try:
        with open(path, 'r', encoding='utf-8') as f:
            users = json.load(f)
        for name, info in users.items():
            user_manager.add_user(name, info.get('client_id', ''), info.get('client_secret', ''))
            if info.get('access_token'):
                user_manager.update_token(name, info['access_token'], info.get('expired_at', ''))
        QMessageBox.information(parent, "导入成功", f"已导入用户: {', '.join(users.keys())}")
    except Exception as e:
        QMessageBox.critical(parent, "导入失败", str(e)) 
