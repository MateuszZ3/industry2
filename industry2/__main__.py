import asyncio
import logging
import sys

from PyQt5.QtWidgets import QApplication

from industry2.factory_gui import MainWindow


if __name__ == '__main__':
    # fix needed for asyncio on Windows [https://github.com/tornadoweb/tornado/issues/2608#issuecomment-550180288]
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    logging.basicConfig(filename='myapp.log', filemode='w', level=logging.DEBUG)
    app = QApplication([])
    window = MainWindow()

    # app.exec()  # TODO
    app.exec_()
    # sys.exit(app.exec_())
