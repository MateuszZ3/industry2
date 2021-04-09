from PyQt5.QtWidgets import QApplication

from industry2.factory_gui import MainWindow

if __name__ == '__main__':
    app = QApplication([])
    window = MainWindow()

    # app.exec()  # TODO
    app.exec_()
    # sys.exit(app.exec_())