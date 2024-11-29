from enum import Enum
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QMainWindow,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QPushButton,
    QStyle,
)


class CustomFieldType(Enum):
    """Enum for the type used by CustomTreeMaker

    These define where the data comes from: from the property sets,
    from attributes of the Ifc element etc.
    """

    IFCCLASS = 1
    OBJECTTYPE = 2
    LINKEDOBJECTTYPE = 3
    PSET = 4
    FILENAME = 5
    CONTAINEDIN = 6


class CustomTreeMaker:
    """Definition for one of the hierarchy levels of a custom tree

    A list of CustomTreeMaker instances can be passed to IfcCustomTreeModel.

    :param fieldtype: Defines how to get the data
    :type fieldtype: CustomFieldType
    :param keys: Tuple of two keys for the PSET dictionary, only needed for CustomFieldType.PSET.
    :type keys: Tuple of str, optional
    """

    def __init__(self, fieldtype, keys=None):
        self.fieldtype = fieldtype
        self.keys = keys
        if self.fieldtype == CustomFieldType.PSET:
            assert isinstance(
                self.keys, tuple
            ), "PSET must have two keys, keys should be tuple"
            assert len(self.keys) == 2, "PSET must have two keys, keys should be tuple"
        else:
            self.keys = None

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.__dict__ == other.__dict__

    def __repr__(self):
        if self.fieldtype == CustomFieldType.PSET:
            return f"CustomTreeMaker {self.fieldtype.name} {self.keys}"
        return f"CustomTreeMaker {self.fieldtype.name}"


class PropertyListItem(QListWidgetItem):
    """Helper class for CustomTreeDialog

    Used in the list view on the right side of the dialog.
    """

    def __init__(self, name, fieldtype, pset_name=None):
        super().__init__(name)
        self.fieldtype = fieldtype
        self.pset_name = pset_name
        self.name = name


class PropertyTreeItem(QTreeWidgetItem):
    """Helper class for CustomTreeDialog

    Used in the tree view on the left side of the dialog.
    """

    def __init__(self, parent, name, fieldtype, pset_name=None):
        super().__init__(parent)
        self.setText(0, name)
        self.name = name
        self.fieldtype = fieldtype
        self.pset_name = pset_name


class CustomTreeDialog(QDialog):
    """Dialog to define a custom tree view

    :param parent: Parent widget (main window)
    """

    def __init__(self, parent):
        super().__init__(parent=parent)
        ifcfiles = parent.ifcfiles
        current_count = len(parent.tabs.customtabs)

        self.defaultname = self.tr("Custom Treeview") + f" {current_count + 1}"

        self.setWindowTitle(self.tr("Create Custom Treeview"))

        layout = QVBoxLayout()

        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel(self.tr("Name")))
        self.name = QLineEdit(self.defaultname)
        name_layout.addWidget(self.name)
        layout.addLayout(name_layout)

        self.left_list = QTreeWidget()
        self.right_list = QListWidget()

        self.left_list.setMinimumWidth(200)
        self.left_list.setMinimumHeight(300)
        self.right_list.setMinimumWidth(200)
        self.left_list.setMinimumHeight(300)

        self.info_item = QTreeWidgetItem(self.left_list)
        self.info_item.setText(0, self.tr("Main attributes"))

        PropertyTreeItem(self.info_item, self.tr("IFC Class"), CustomFieldType.IFCCLASS)
        PropertyTreeItem(
            self.info_item, self.tr("ObjectType attribute"), CustomFieldType.OBJECTTYPE
        )
        PropertyTreeItem(
            self.info_item,
            self.tr("Linked Object Type"),
            CustomFieldType.LINKEDOBJECTTYPE,
        )
        PropertyTreeItem(self.info_item, self.tr("Filename"), CustomFieldType.FILENAME)
        PropertyTreeItem(
            self.info_item, self.tr("Contained in"), CustomFieldType.CONTAINEDIN
        )

        pset_info = ifcfiles.pset_info

        for pset_name in pset_info.keys():
            pset_item = QTreeWidgetItem(self.left_list)
            pset_item.setText(0, pset_name)
            for prop in pset_info[pset_name]:
                PropertyTreeItem(pset_item, prop, CustomFieldType.PSET, pset_name)

        self.left_list.expandAll()
        self.left_list.setHeaderHidden(True)

        list_layout = QHBoxLayout()
        left_button_layout = QVBoxLayout()
        right_button_layout = QVBoxLayout()

        list_layout.addWidget(self.left_list)
        list_layout.addLayout(left_button_layout)
        list_layout.addWidget(self.right_list)
        list_layout.addLayout(right_button_layout)

        add_button = QPushButton("")
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowForward)
        add_button.setIcon(icon)
        remove_button = QPushButton("")
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowBack)
        remove_button.setIcon(icon)

        up_button = QPushButton("")
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp)
        up_button.setIcon(icon)
        down_button = QPushButton("")
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown)
        down_button.setIcon(icon)

        left_button_layout.addStretch()
        left_button_layout.addWidget(add_button)
        left_button_layout.addWidget(remove_button)
        left_button_layout.addStretch()
        right_button_layout.addStretch()
        right_button_layout.addWidget(up_button)
        right_button_layout.addWidget(down_button)
        right_button_layout.addStretch()

        add_button.clicked.connect(self.add_item)
        remove_button.clicked.connect(self.remove_item)
        up_button.clicked.connect(self.move_item_up)
        down_button.clicked.connect(self.move_item_down)

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout.addSpacing(10)
        layout.addLayout(list_layout)
        layout.addSpacing(20)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)

    def add_item(self):
        """Takes an item of the treeview on the left and adds it in the list on the right"""
        selected_items = self.left_list.selectedItems()
        for item in selected_items:
            if item.parent() is not None:
                prop_item = PropertyListItem(item.name, item.fieldtype, item.pset_name)
                self.right_list.addItem(prop_item)
                item.parent().removeChild(item)

    def remove_item(self):
        """Removes an item in the list on the right and adds it again on the left"""
        selected_items = self.right_list.selectedItems()
        for item in selected_items:
            self.right_list.takeItem(self.right_list.row(item))
            if item.fieldtype == CustomFieldType.PSET:
                # pset_text = item.pset_name
                for i in range(1, self.left_list.topLevelItemCount()):
                    pset_item = self.left_list.topLevelItem(i)
                    if pset_item.text(0) == item.pset_name:
                        parent_item = pset_item
                        break
            else:
                parent_item = self.info_item
            PropertyTreeItem(parent_item, item.name, item.fieldtype, item.pset_name)

    def move_item_up(self):
        """Move item up in the list on the right side"""
        current_row = self.right_list.currentRow()
        if current_row > 0:
            item = self.right_list.takeItem(current_row)
            self.right_list.insertItem(current_row - 1, item)
            self.right_list.setCurrentItem(item)

    def move_item_down(self):
        """Move item up the list on the right side"""
        current_row = self.right_list.currentRow()
        if current_row < self.right_list.count() - 1:
            item = self.right_list.takeItem(current_row)
            self.right_list.insertItem(current_row + 1, item)
            self.right_list.setCurrentItem(item)

    def get_name(self):
        """Get the text from the name input field"""
        name = self.name.text().strip()
        if name == "":
            return self.defaultname
        return name

    def get_items(self):
        """Get CustomTreeMaker items

        Turns the items of the listview to CustomTreeMaker instances
        and returns them
        :rtype: list of CustomTreeMaker
        """
        items = []
        for i in range(self.right_list.count()):
            item = self.right_list.item(i)
            custom_field = CustomTreeMaker(item.fieldtype, (item.pset_name, item.name))
            items.append(custom_field)
        return items
