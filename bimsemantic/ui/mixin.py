from PySide6.QtWidgets import QTreeView, QApplication, QMenu
from PySide6.QtGui import QAction


class CopyMixin:
    """Mixin class for dock widgets to copy data

    Only for docks with a treeview and with a
    selection policy of selecting rows.
    """

    def copy_active_cell_to_clipboard(self):
        """Copy the active cell to the clipboard"""
        if hasattr(self, "overviewtree"):
            # This is the detail dock, the tree can change (overviewtree or not)
            tree = self.widget()
        else:
            tree = self.tree

        index = tree.currentIndex()
        if index.isValid():
            data = index.data()
            if data is not None:
                data = str(data)
            else:
                data = ""
            clipboard = QApplication.clipboard()
            clipboard.setText(data)

    def copy_selection_to_clipboard(self):
        """Copy the active row to the clipboard"""
        if hasattr(self, "overviewtree"):
            # This is the detail dock, it does not have a proxy model and 
            # the tree can change (overviewtree or not)
            tree = self.widget()
            model = tree.model()
            proxymodel = None
        else:
            tree = self.tree
            model = self.treemodel
            proxymodel = self.proxymodel

        # Index of active cell
        index = tree.currentIndex()
        if index.isValid():
            row = index.row()
            parent = index.parent()

            data = []
            # Iterate through the columns of the active row
            for col in range(model.columnCount()):
                if tree.isColumnHidden(col):
                    continue
                if proxymodel:
                    index = proxymodel.index(row, col, parent)
                else:
                    index = model.index(row, col, parent)
                row_data = index.data()
                if row_data is not None:
                    data.append(str(row_data))
                else:
                    data.append("")

            add_level = self.mainwindow.chk_copy_with_level.isChecked()
            if add_level:
                if proxymodel is not None:
                    index = proxymodel.mapToSource(index)
                item = index.internalPointer()
                level = item.level()
                data.insert(0, str(level))     

            data = "\t".join(data)


            if self.mainwindow.chk_copy_with_headers.isChecked() and proxymodel is not None:
                # the detail view does not have a header and does not have a proxy model
                header = []
                if add_level:
                    header.append("Level")
                for col in range(model.columnCount()):
                    if tree.isColumnHidden(col):
                        continue
                    header.append(str(model.headerData(col)))
                header = "\t".join(header)
                data = header + "\n" + data


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

        if hasattr(self, "get_validator_id"):
            # Only true for validation dock
            context_menu.addAction(self.mainwindow.run_selected_validation_act)
            context_menu.addSeparator()
            if index.isValid():
                original_index = self.proxymodel.mapToSource(index)
                item = original_index.internalPointer()
                if not self.get_validator_id(item) == 'integrity':
                    context_menu.addAction(self.mainwindow.edit_ids_act)
                    context_menu.addAction(self.mainwindow.edit_ids_copy_act)
                    context_menu.addAction(self.mainwindow.close_ids_act)
                    context_menu.addSeparator()


        context_menu.addAction(self.mainwindow.copy_rows_act)
        context_menu.addAction(self.mainwindow.copy_cell_act)

        if self.mainwindow.somdock and self.mainwindow.somdock.isVisible():
            context_menu.addAction(self.mainwindow.search_som_act)

            if hasattr(self, "get_pset_tuple") and index.isValid():
                pset_tuple = self.get_pset_tuple(index)
                if pset_tuple:
                    autosearch_action = QAction(
                        self.tr("SOM autosearch %s" % pset_tuple[1]),
                        self,
                        triggered=lambda: self.mainwindow.somdock.set_autosearch_attribute(
                            pset_tuple
                        ),
                    )
                    context_menu.addAction(autosearch_action)

        # Detail view: show overview
        if hasattr(self, "overviewtree") and self.overviewtree != self.widget():
            context_menu.addAction(self.mainwindow.overview_act)

        context_menu.exec(tree.viewport().mapToGlobal(position))
