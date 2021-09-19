import asyncio
import sys

from PyQt5.QtWidgets import QApplication

from industry2.factory_gui import MainWindow


if __name__ == '__main__':
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    app = QApplication([])
    window = MainWindow()

    # app.exec()  # TODO
    app.exec_()
    # sys.exit(app.exec_())
