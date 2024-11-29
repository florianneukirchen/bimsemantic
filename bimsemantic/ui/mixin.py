from PySide6.QtWidgets import QTreeView, QApplication, QMenu
from PySide6.QtGui import QAction

class CopyMixin:
    """Mixin class for dock widgets to copy data
    
    Only for docks with a treeview and with a 
    selection policy of selecting rows.
    """
    def copy_active_cell_to_clipboard(self):
        """Copy the active cell to the clipboard"""
        widget = self.widget()
        if not widget:
            return
        if isinstance(widget, QTreeView):
            tree = widget
        else:
            # The main widget of the dock is not the treeview
            try:
                tree = widget.parent().tree
            except AttributeError:
                return
            
        index = tree.currentIndex()
        if index.isValid():
            data = index.data()
            if data:
                data = str(data)
            else:
                data = ""
            clipboard = QApplication.clipboard()
            clipboard.setText(data)   

    def copy_selection_to_clipboard(self):
        """Copy the active row to the clipboard"""
        widget = self.widget()
        if not widget:
            return
        if isinstance(widget, QTreeView):
            tree = widget
        else:
            # The main widget of the dock is not the treeview
            try:
                tree = widget.parent().tree
            except AttributeError:
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


class ContextMixin:
    """Mixin class for docks to show context menus"""
    def show_context_menu(self, position):
        """Show the context menu at the given position"""
        widget = self.widget()
        if not widget:
            return
        if isinstance(widget, QTreeView):
            tree = widget
        else:
            # The main widget of the dock is not the treeview
            try:
                tree = widget.parent().tree
            except AttributeError:
                return
            
        index = tree.indexAt(position)

        context_menu = QMenu(self)
        context_menu.addAction(self.mainwindow.copy_rows_act)
        context_menu.addAction(self.mainwindow.copy_cell_act)

        if self.mainwindow.somdock and self.mainwindow.somdock.isVisible():
            context_menu.addAction(self.mainwindow.search_som_act)
        
            if hasattr(self, "get_pset_tuple") and index.isValid():
                pset_tuple = self.get_pset_tuple(index)
                if pset_tuple:
                    autosearch_action = QAction(
                        self.tr("Autosearch"), 
                        self,
                        triggered=lambda: self.mainwindow.somdock.set_autosearch_attribute(pset_tuple))
                    context_menu.addAction(autosearch_action)
            
        context_menu.exec(tree.viewport().mapToGlobal(position))