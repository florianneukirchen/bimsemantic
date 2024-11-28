from PySide6.QtWidgets import QTreeView, QApplication


class CopyMixin:
    """Mixin class for dock widgets to copy data
    
    Only for docks with a treeview and with a 
    selection policy of selecting rows.
    """
    def copy_active_cell_to_clipboard(self):
        """Copy the active cell to the clipboard"""
        tree = self.widget()
        if not tree or not isinstance(tree, QTreeView):
            return
        index = tree.currentIndex()
        if index.isValid():
            data = index.data()
            clipboard = QApplication.clipboard()
            clipboard.setText(data)   

    def copy_selection_to_clipboard(self):
        """Copy the active row to the clipboard"""
        tree = self.widget()
        if not tree or not isinstance(tree, QTreeView):
            return
        index = tree.currentIndex()
        if index.isValid():
            row = index.row()
            parent = index.parent()
            model = tree.model()
            data = []
            for col in range(model.columnCount()):
                if tree.isColumnHidden(col):
                    continue
                index = model.index(row, col, parent)
                row_data = index.data()
                if row_data:
                    data.append(str(row_data))
                else:
                    data.append("")
            data = "\t".join(data)
            clipboard = QApplication.clipboard()
            clipboard.setText(data)   