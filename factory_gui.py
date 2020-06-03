import sys
import time
import traceback
from math import sin, cos

from PyQt5 import QtGui
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from spade import quit_spade

import settings
from agents import FactoryAgent


COLORS = [
    # 17 undertones https://lospec.com/palette-list/17undertones
    '#000000', '#141923', '#414168', '#3a7fa7', '#35e3e3', '#8fd970', '#5ebb49',
    '#458352', '#dcd37b', '#fffee5', '#ffd035', '#cc9245', '#a15c3e', '#a42f3b',
    '#f45b7a', '#c24998', '#81588d', '#bcb0c2', '#d7d7d7', '#ffffff',
]


class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.

    Supported signals are:

    finished
        No data

    error
        `tuple` (exctype, value, traceback.format_exc() )

    result
        `object` data returned from processing, anything

    progress
        `int` indicating % progress

    """
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)


class Worker(QRunnable):
    """
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    """

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        # Add the callback to our kwargs
        self.kwargs['update_callback'] = self.signals.progress

    @pyqtSlot()
    def run(self):
        """
        Initialise the runner function with passed args, kwargs.
        """

        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done


class Canvas(QLabel):

    def __init__(self, factory_agent):
        super().__init__()
        # Color definitions
        self.gom_color = QtGui.QColor(COLORS[3])
        self.tr_color = QtGui.QColor(COLORS[14])
        self.aside_color = QtGui.QColor(COLORS[2])
        self.bg_color = QtGui.QColor(COLORS[-2])

        pixmap = QtGui.QPixmap(self.width(),self.height())
        pixmap = pixmap.scaled(self.width(), self.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        pixmap.fill(self.bg_color)
        self.setPixmap(pixmap)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(10, 10)

        self.factory_agent = factory_agent
        self.agents = [QPoint(0, 0)]

    def resizeEvent(self, event) -> None:
        pixmap = QtGui.QPixmap(self.width(),self.height())
        pixmap.fill(self.bg_color)
        pixmap = pixmap.scaled(self.width(), self.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setPixmap(pixmap)

    def clear_scene(self) -> None:
        """
        Clears scene but DOES NOT call update.
        """

        pixmap = self.pixmap()
        pixmap.fill(QtGui.QColor(COLORS[-2]))
        self.update()

    def draw_scene(self) -> None:
        # TODO remove first position in gom_positions and tr_positions, use factory_map
        self.clear_scene()
        painter = QtGui.QPainter(self.pixmap())
        p = painter.pen()

        # Draw set-aside
        p.setWidth(12)
        p.setColor(self.aside_color)
        painter.setPen(p)
        self.draw_point(self.factory_agent.gom_positions[0], painter)

        p.setColor(self.gom_color)
        painter.setPen(p)
        for gom in self.factory_agent.gom_positions[1:]:
            self.draw_point(gom, painter)

        # Draw TRs
        p.setWidth(4)
        p.setColor(self.tr_color)
        painter.setPen(p)

        for tr in self.factory_agent.tr_positions[1:]:
            self.draw_point(tr, painter)

        painter.end()
        self.update()

    def draw_point(self, point, painter) -> None:
        """
        Draws point with painter. (0, 0) is centered.
        """

        if point is not None:
            x = round(self.width() / 2 + point.x)
            y = round(self.height() / 2 - point.y)
            painter.drawPoint(x, y)


class MainWindow(QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        # Agent
        self.factory_agent = FactoryAgent(f"{settings.AGENT_NAMES['factory']}@{settings.HOST}", settings.PASSWORD)

        # Layout
        layout = QVBoxLayout()

        self.canvas = Canvas(self.factory_agent)
        b = QPushButton("Start worker")
        b.pressed.connect(self.start_agent_worker)

        layout.addWidget(self.canvas)
        layout.addWidget(b)

        w = QWidget()
        w.setLayout(layout)
        self.setCentralWidget(w)

        self.show()

        # Multithreading
        self.thread_pool = QThreadPool()
        print("Multithreading with maximum %d threads" % self.thread_pool.maxThreadCount())

        # tmp
        self.counter = 0
        self.timer = QTimer()
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.recurring_timer)
        self.timer.start()

    def progress_fn(self, n) -> None:
        print(f"[progress_fn] {n}")

    def execute_agent(self, update_callback):
        agent = self.factory_agent
        agent.set_update_callback(update_callback)
        future = agent.start()
        future.result()

        while agent.is_alive():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                agent.stop()
                break

        print("Agent finished")
        future = agent.stop()
        future.result()
        quit_spade()

        return "Successful result"

    def process_result(self, result) -> None:
        print(f"Worker result:\n{result}")

    def thread_complete(self) -> None:
        print("THREAD COMPLETE!")

    def start_agent_worker(self) -> None:
        """
        Binds defined signals, then starts factory agent in separate thread.
        """
        # Pass the function to execute
        worker = Worker(self.execute_agent)  # Any other args, kwargs are passed to the run function
        worker.signals.result.connect(self.process_result)
        worker.signals.finished.connect(self.thread_complete)
        worker.signals.progress.connect(self.progress_fn)

        # Execute
        self.thread_pool.start(worker)

    def recurring_timer(self) -> None:
        self.counter += 0.05
        self.canvas.agents[0].setX(round(cos(self.counter) * 100) + 120)
        self.canvas.agents[0].setY(round(sin(self.counter) * 100) + 120)
        self.canvas.draw_scene()


app = QApplication([])
window = MainWindow()
app.exec_()
