import os
import subprocess
from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem, QAbstractItemView, QMenu, QInputDialog
from PyQt6.QtCore import Qt

class DragDropTreeWidget(QTreeWidget):
    def __init__(self):
        super().__init__()
        self.setHeaderLabels(["檔案路徑 / 分組 (Part)"])
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.valid_exts = ('.MP4', '.JPG', '.JPEG', '.PNG')

    def show_context_menu(self, position):
        item = self.itemAt(position)
        if not item: return

        selected_items = self.selectedItems()
        if item not in selected_items:
            self.clearSelection()
            item.setSelected(True)
            selected_items = [item]

        menu = QMenu()
        menu.setStyleSheet("QMenu { background-color: #2b2b2b; color: white; border: 1px solid #555; } QMenu::item:selected { background-color: #005A9E; }")
        
        if len(selected_items) > 1:
            delete_action = menu.addAction(f"🗑️ 移除所選的 {len(selected_items)} 個項目")
            action = menu.exec(self.viewport().mapToGlobal(position))
            if action == delete_action:
                self.batch_delete(selected_items)
        else:
            is_part = item.parent() is None
            if is_part:
                rename_action = menu.addAction("✏️ 重新命名 Part")
                sort_action = menu.addAction("🔡 智慧排序 (依時間與檔名)")
                delete_action = menu.addAction("🗑️ 移除此 Part")
                action = menu.exec(self.viewport().mapToGlobal(position))
                
                if action == rename_action:
                    self.rename_part(item)
                elif action == sort_action:
                    self.smart_sort_part(item)
                elif action == delete_action:
                    self.takeTopLevelItem(self.indexOfTopLevelItem(item))
            else:
                open_folder_action = menu.addAction("📂 開啟檔案所在位置")
                remove_file_action = menu.addAction("❌ 從清單移除")
                action = menu.exec(self.viewport().mapToGlobal(position))
                
                if action == open_folder_action:
                    subprocess.Popen(f'explorer /select,"{item.text(0)}"')
                elif action == remove_file_action:
                    item.parent().removeChild(item)

    def rename_part(self, item):
        new_name, ok = QInputDialog.getText(self, "重新命名 Part", "請輸入新的名稱:", text=item.text(0))
        if ok and new_name.strip(): item.setText(0, new_name.strip())

    def smart_sort_part(self, part_item):
        """針對單一 Part 內的檔案進行智慧排序"""
        children = []
        for i in range(part_item.childCount()):
            children.append(part_item.takeChild(0))
        
        # 排序邏輯：優先處理 GoPro 命名規則，其餘依修改時間
        def sort_key(child):
            path = child.text(0)
            fname = os.path.basename(path).upper()
            if fname.startswith('GX') and len(fname) >= 12:
                return (0, fname[4:8], fname[2:4]) # 群組ID, 章節
            return (1, os.path.getmtime(path), fname)
        
        children.sort(key=sort_key)
        part_item.addChildren(children)

    def batch_delete(self, selected_items):
        items_to_delete = []
        for sel_item in selected_items:
            if sel_item.parent() is not None and sel_item.parent() in selected_items:
                continue
            items_to_delete.append(sel_item)
        for sel_item in items_to_delete:
            if sel_item.parent() is None:
                self.takeTopLevelItem(self.indexOfTopLevelItem(sel_item))
            else:
                sel_item.parent().removeChild(sel_item)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()
        else: super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()
        else: super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if os.path.isfile(path) and path.upper().endswith(self.valid_exts):
                    self.addTopLevelItem(QTreeWidgetItem([path]))
                elif os.path.isdir(path):
                    for f in os.listdir(path):
                        if f.upper().endswith(self.valid_exts):
                            self.addTopLevelItem(QTreeWidgetItem([os.path.normpath(os.path.join(path, f))]))
            event.acceptProposedAction()
        else: super().dropEvent(event)