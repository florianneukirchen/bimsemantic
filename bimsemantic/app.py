import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTranslator, QLocale, QLibraryInfo

# Add package to python path
package_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, package_root)

from bimsemantic.ui import MainWindow


if __name__ == "__main__":
    app = QApplication(sys.argv)

    translator = QTranslator(app)
    locale = QLocale.system().name()
    language_code = locale.split("_")[0]
    translation_file = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        "i18n",
        f"bimsemantic_{language_code}.qm",
    )
    if translator.load(translation_file):
        app.installTranslator(translator)
    elif language_code != "en":
        print(f"Translation file for locale '{locale}' not found.")

    qt_translator = QTranslator(app)
    qt_translations_path = QLibraryInfo.path(QLibraryInfo.TranslationsPath)
    if qt_translator.load(QLocale(), "qtbase", "_", qt_translations_path):
        app.installTranslator(qt_translator)
    else:
        print("Qt base translations not found!")

    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())
