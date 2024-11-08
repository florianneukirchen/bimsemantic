import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTranslator, QLocale

# Add package to python path
package_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, package_root)

from bimsemantic.ui import MainWindow



if __name__ == "__main__":
    app = QApplication(sys.argv)

    translator = QTranslator(app)
    locale = QLocale.system().name()
    language_code = locale.split('_')[0]
    translation_file = os.path.join(package_root, "bimsemantic", "i18n", f"bimsemantic_{language_code}.qm")
    if translator.load(translation_file):
        app.installTranslator(translator)
    elif language_code != "en":
        print(f"Translation file for locale '{locale}' not found.")

    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())
