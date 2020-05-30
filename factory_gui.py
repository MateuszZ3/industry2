from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from PyQt5 import QtGui, uic

import time
import traceback, sys
from math import sin, cos
from random import randint

from factory_agent import FactoryAgent
from spade import quit_spade

COLORS = [
    # 17 undertones https://lospec.com/palette-list/17undertones
    '#000000', '#141923', '#414168', '#3a7fa7', '#35e3e3', '#8fd970', '#5ebb49',
    '#458352', '#dcd37b', '#fffee5', '#ffd035', '#cc9245', '#a15c3e', '#a42f3b',
    '#f45b7a', '#c24998', '#81588d', '#bcb0c2', '#ffffff',
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
        self.kwargs['progress_callback'] = self.signals.progress

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

    def __init__(self):
        super().__init__()
        pixmap = QtGui.QPixmap(600, 300)
        self.setPixmap(pixmap)
        self.pen_color = QtGui.QColor(COLORS[3])
        self.bounding_rect = QRect(0, 0, self.width(), self.height())

        self.points = [QPoint(0, 0)]

    def add_point(self, pt):
        self.points.append(pt)

    def clear_scene(self):
        """
        Clears scene but DOES NOT call update.
        """

        painter = QtGui.QPainter(self.pixmap())
        painter.fillRect(self.bounding_rect, QtGui.QColor(COLORS[-1]))
        painter.end()

    def draw_scene(self):
        self.clear_scene()

        painter = QtGui.QPainter(self.pixmap())
        p = painter.pen()
        p.setWidth(4)
        p.setColor(self.pen_color)
        painter.setPen(p)

        # Draw test points
        for pt in self.points:
            painter.drawPoint(pt)

        painter.end()
        self.update()


class MainWindow(QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        # Agent
        self.factory_agent = FactoryAgent("agent@localhost", "password")

        # Layout
        layout = QVBoxLayout()

        self.canvas = Canvas()
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

    def progress_fn(self, n):
        print("[progress_fn] %d%% done" % n)

    def execute_agent(self, progress_callback):
        agent = self.factory_agent
        agent.set_progress_callback(progress_callback)
        future = agent.start()
        future.result()

        while not agent.ticker_behav.is_killed():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                agent.stop()
                break

        print("Agent finished")
        future = agent.stop()
        future.result()
        quit_spade()

        result = QPoint(
            200 + randint(-100, 100),  # x
            150 + randint(-100, 100)  # Y
        )

        return result

    def process_result(self, result):
        self.canvas.add_point(result)

    def thread_complete(self):
        print("THREAD COMPLETE!")

    def start_agent_worker(self):
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

    def recurring_timer(self):
        self.counter += 0.05
        self.canvas.points[0].setX(round(cos(self.counter) * 100) + 120)
        self.canvas.points[0].setY(round(sin(self.counter) * 100) + 120)
        self.canvas.draw_scene()


app = QApplication([])
window = MainWindow()
app.exec_()
