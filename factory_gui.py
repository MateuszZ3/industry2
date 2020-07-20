import sys
import time
import traceback

from PyQt5 import QtGui
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from spade import quit_spade

import settings
from common import Point
from common import clip
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
        `bool` indicating whether to redraw scene

    """
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(bool)


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
        self.font_color = QtGui.QColor(COLORS[0])

        pixmap = QtGui.QPixmap(self.width(), self.height())
        pixmap = pixmap.scaled(self.width(), self.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        pixmap.fill(self.bg_color)
        self.setPixmap(pixmap)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(10, 10)
        self.zoom = 2.5
        self.min_zoom, self.max_zoom = 0.5, 5.0
        self.offset_x, self.offset_y = 0.0, 0.0

        # Font
        font = QtGui.QFont()
        font.setBold(True)
        font.setPointSize(40)
        painter = QtGui.QPainter(self.pixmap())
        painter.setFont(font)

        self.factory_agent = factory_agent
        self.agents = [QPoint(0, 0)]

    def resizeEvent(self, event) -> None:
        pixmap = QtGui.QPixmap(self.width(), self.height())
        pixmap.fill(self.bg_color)
        pixmap = pixmap.scaled(self.width(), self.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setPixmap(pixmap)

    def clear_scene(self) -> None:
        """
        Clears scene.
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
        p.setWidth(round(12 * self.zoom))
        p.setColor(self.aside_color)
        painter.setPen(p)
        self.draw_point(self.factory_agent.factory_map[""], painter)

        # Draw GoMs

        for jid in self.factory_agent.factory_map:
            if jid != "":  # set-aside already drawn
                p.setColor(self.gom_color)
                painter.setPen(p)

                pt = self.factory_agent.factory_map[jid]
                self.draw_point(pt, painter)

                p.setColor(self.font_color)  # TODO: optimize color swapping
                painter.setPen(p)
                self.draw_text(pt, 12, painter, 'GoM 101')

        # Draw TRs
        p.setWidth(round(4 * self.zoom))

        for jid in self.factory_agent.tr_map:
            p.setColor(self.tr_color)
            painter.setPen(p)

            pt = self.factory_agent.tr_map[jid]
            self.draw_point(pt, painter)

            p.setColor(self.font_color)  # TODO: optimize color swapping
            painter.setPen(p)
            self.draw_text(pt, 4, painter, jid)

        painter.end()
        self.update()

    def draw_point(self, point, painter) -> None:
        """
        Draws point with painter. (0, 0) is centered.
        """

        if point is not None:
            x, y = self.translate_point(point)
            painter.drawPoint(x, y)

    def draw_text(self, point: Point, bb_size: int, painter: QtGui.QPainter, text: str) -> None:
        """
        :param pt: Point on map in absolute units.
        Draws `text` with `painter` relatively to `point`. (0, 0) is centered.
        Text is rendered `bb_size` units under `point`.
        """

        if point is not None:
            pt = Point(point.x, point.y - bb_size)
            x, y = self.translate_point(pt)
            painter.drawText(x - 50, y, 100, 100, Qt.AlignBaseline | Qt.AlignHCenter, text)

    def translate_point(self, point: Point) -> (float, float):
        """
        :param point: Point on map in absolute units.
        :return: Tuple of coordinates translated to position in pixels.
        """

        x = round(self.width() / 2 + (point.x - self.offset_x) * self.zoom)
        y = round(self.height() / 2 - (point.y - self.offset_y) * self.zoom)
        return x, y

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

        # Redraw scene every 100ms
        self.timer = QTimer()
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.recurring_timer)
        self.timer.start()

        # Mouse events
        self.last_x, self.last_y = None, None

    def progress_fn(self, flag) -> None:
        print(f"[progress_fn] {flag}")

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
        self.canvas.draw_scene()

    def mouseMoveEvent(self, e) -> None:
        if self.last_x is None:  # First event.
            self.last_x = e.x()
            self.last_y = e.y()
            return  # Ignore the first time.

        # Move scene offset depending on zoom level
        dx, dy = self.last_x - e.x(), self.last_y - e.y()
        self.canvas.offset_x += dx / self.canvas.zoom
        self.canvas.offset_y -= dy / self.canvas.zoom
        # print(f'{dx}, {dy}')
        self.canvas.draw_scene()

        # Update the origin for next time.
        self.last_x = e.x()
        self.last_y = e.y()

    def mouseReleaseEvent(self, e) -> None:
        self.last_x = None
        self.last_y = None


    def wheelEvent(self, e) -> None:
        nz = self.canvas.zoom + e.angleDelta().y() / 1200
        self.canvas.zoom = clip(nz, self.canvas.min_zoom, self.canvas.max_zoom)
        self.canvas.draw_scene()


app = QApplication([])
window = MainWindow()
app.exec_()
