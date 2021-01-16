import sys
import time
import traceback
import re

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


class ViewModel:
    def __init__(self, set_description_text_callback):
        """
        Factory view model. Holds all necessary data.

        :param set_description_text_callback: Callback to be used after setting description text.
        """
        self.tr_list = {}  # Deepcopy before sending
        self.tr_map = {}  # Deepcopy before sending
        self.factory_map = {}  # it don't matter but copy

        self._selected_tr_jid = None

        self._description_text = ""
        self._set_description_text_callback = set_description_text_callback

    def set_description_text(self, text: str) -> None:
        """Sets text content of description widget."""
        self._set_description_text_callback(text)

    def select_tr(self, jid) -> None:
        """Handles selection of TR with given JID."""
        if jid == "":
            self._selected_tr_jid = None
            self.set_description_text("")
        else:
            self._selected_tr_jid = jid
            self.set_description_text(jid)

    def get_selected_tr_jid(self):
        """Returns currently selected TR agent JID."""
        return self._selected_tr_jid


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

    tr_position_update
        `str` tr_jid
        `object` Point

    """
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    update_tr_position = pyqtSignal(str, object)
    update_view_model = pyqtSignal(object, object, object)


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
        self.kwargs['update_tr_position_callback'] = self.signals.update_tr_position
        self.kwargs['update_view_model_callback'] = self.signals.update_view_model

    @pyqtSlot()
    def run(self):
        """Initialise the runner function with passed args, kwargs."""
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
    """Canvas representing factory map."""
    def __init__(self, view_model):
        super().__init__()

        # Color definitions
        self.gom_color = QtGui.QColor(COLORS[3])
        self.tr_color = QtGui.QColor(COLORS[14])
        self.aside_color = QtGui.QColor(COLORS[2])
        self.bg_color = QtGui.QColor(COLORS[-2])
        self.font_color = QtGui.QColor(COLORS[0])
        self.connection_color = QtGui.QColor(COLORS[11])
        self.connection_color.setAlphaF(0.2)
        self.connection_hover_color = QtGui.QColor(COLORS[11])
        self.connection_hover_color.setAlphaF(0.9)

        pixmap = QtGui.QPixmap(self.width(), self.height())
        pixmap = pixmap.scaled(self.width(), self.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        pixmap.fill(self.bg_color)
        self.setPixmap(pixmap)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(10, 10)
        self.zoom = settings.ZOOM_DEFAULT
        self.min_zoom, self.max_zoom = settings.ZOOM_MIN, settings.ZOOM_MAX
        self.offset_x, self.offset_y = 0.0, 0.0

        # Font
        font = QtGui.QFont()
        font.setBold(True)
        font.setPointSize(40)
        painter = QtGui.QPainter(self.pixmap())
        painter.setFont(font)

        self.factory_view_model = view_model

        # Mouse events
        self.last_x, self.last_y = None, None
        self.hover_radius = settings.HOVER_RADIUS

        # self.setMouseTracking(True)
        # self.setCursor(Qt.ClosedHandCursor)
        # self.setCursor(Qt.PointingHandCursor)  # On moving

    def resizeEvent(self, event) -> None:
        pixmap = QtGui.QPixmap(self.width(), self.height())
        pixmap.fill(self.bg_color)
        pixmap = pixmap.scaled(self.width(), self.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setPixmap(pixmap)

    def draw_scene(self) -> None:
        # TODO remove first position in gom_positions and tr_positions, use factory_map
        self.clear_scene()
        painter = QtGui.QPainter(self.pixmap())
        p = painter.pen()

        # Draw set-aside
        p.setWidthF(round(12 * self.zoom))
        p.setColor(self.aside_color)
        painter.setPen(p)
        if "" in self.factory_view_model.factory_map:
            self.draw_point(self.factory_view_model.factory_map[""], painter)

        # Draw GoMs
        for jid in self.factory_view_model.factory_map:
            if jid != "":  # set-aside already drawn
                p.setColor(self.gom_color)
                painter.setPen(p)

                pt = self.factory_view_model.factory_map[jid]
                self.draw_point(pt, painter)

                p.setColor(self.font_color)  # TODO: optimize color swapping
                painter.setPen(p)

                name = ""
                try:
                    name = re.split("@", jid)[0]
                except Exception as e:
                    print(f"JID Error. Bad JID: {jid}")
                    print(repr(e))
                finally:
                    self.draw_text(pt, 12, painter, f"{name.upper()}")

        # Draw TR connections
        for jid in self.factory_view_model.tr_list:
            master = self.factory_view_model.tr_list[jid]
            # TODO: Handle hover
            if self.factory_view_model.get_selected_tr_jid() == jid:
                p.setWidthF(round(1.25 * self.zoom))
                p.setColor(self.connection_hover_color)
            else:
                p.setWidthF(round(0.75 * self.zoom))
                p.setColor(self.connection_color)
            painter.setPen(p)

            # Get coordinates for master-TR
            pt = self.factory_view_model.tr_map[jid]

            # TODO: Make sure `master.coworkers` doesn't change while drawing,
            #       aka enable copying tr_list.
            # Get coordinates for coworkers
            for coworker_jid in master.coworkers:
                coworker_pt = self.factory_view_model.tr_map[coworker_jid]
                # Draw connection
                self.draw_line(pt, coworker_pt, painter)

        # Draw TRs
        p.setWidthF(round(4 * self.zoom))

        for jid in self.factory_view_model.tr_map:
            p.setColor(self.tr_color)
            painter.setPen(p)

            pt = self.factory_view_model.tr_map[jid]
            self.draw_point(pt, painter)

            p.setColor(self.font_color)  # TODO: optimize color swapping
            painter.setPen(p)

            name = ""
            try:
                name = re.split("@", jid)[0]
            except Exception as e:
                print(f"JID Error. Bad JID: {jid}")
                print(repr(e))
            finally:
                self.draw_text(pt, 4, painter, f"{name.upper()}")

        painter.end()
        self.update()

    def clear_scene(self) -> None:
        """Clears scene."""
        pixmap = self.pixmap()
        pixmap.fill(QtGui.QColor(COLORS[-2]))
        self.update()

    def mouseMoveEvent(self, e) -> None:
        # Try to select a TR
        self.handle_hover(e.x(), e.y())

        if self.last_x is None:  # First event.
            self.last_x = e.x()
            self.last_y = e.y()

            return  # Ignore the first time.

        # Move scene offset depending on zoom level
        dx, dy = self.last_x - e.x(), self.last_y - e.y()
        self.offset_x += dx / self.zoom
        self.offset_y -= dy / self.zoom
        self.draw_scene()

        # Update the origin for next time.
        self.last_x = e.x()
        self.last_y = e.y()

    def mouseReleaseEvent(self, e) -> None:
        self.last_x = None
        self.last_y = None

    def wheelEvent(self, e) -> None:
        nz = self.zoom + e.angleDelta().y() / 1200
        self.zoom = clip(nz, self.min_zoom, self.max_zoom)
        self.draw_scene()

    def handle_hover(self, x, y) -> bool:
        abs_pos = self.translate_window_to_map(x, y)

        for jid in self.factory_view_model.tr_map:
            if self.in_radius(self.factory_view_model.tr_map[jid], abs_pos, self.hover_radius):
                self.factory_view_model.select_tr(jid)
                return True

        self.factory_view_model.select_tr(None)
        return False

    def draw_point(self, point: Point, painter: QtGui.QPainter) -> None:
        """Draws point with painter. (0, 0) is centered."""
        if point is not None:
            x, y = self.translate_map_to_window(point)
            painter.drawPoint(x, y)

    def draw_line(self, p1: Point, p2: Point, painter: QtGui.QPainter) -> None:
        """Draws line from p1 to p2 with painter. (0, 0) is centered."""
        if p1 is not None and p2 is not None:
            x1, y1 = self.translate_map_to_window(p1)
            x2, y2 = self.translate_map_to_window(p2)
            painter.drawLine(x1, y1, x2, y2)

    def draw_text(self, point: Point, bb_size: int, painter: QtGui.QPainter, text: str) -> None:
        """
        Draws `text` with `painter` relatively to `point`. (0, 0) is centered.
        Text is rendered `bb_size` units under `point`.

        :param point: Point on map in absolute units.
        :param bb_size: Bounding box size. Essentially margin.
        :param painter: Painter.
        :param text: Text content.
        """
        if point is not None:
            pt = Point(point.x, point.y - bb_size)
            x, y = self.translate_map_to_window(pt)
            painter.drawText(x - 50, y, 100, 100, Qt.AlignBaseline | Qt.AlignHCenter, text)

    def translate_map_to_window(self, point: Point) -> (float, float):
        """
        Translates point from map coordinates to window coordinates (pixels).

        :param point: Point on map in absolute units.
        :return: Tuple of coordinates translated to position in pixels.
        """
        x = round(self.width() / 2 + (point.x - self.offset_x) * self.zoom)
        y = round(self.height() / 2 - (point.y - self.offset_y) * self.zoom)
        return x, y

    def translate_window_to_map(self, x: float, y: float) -> Point:
        """
        Translates point from window coordinates (pixels) to position on map.

        :param x: Pixel X position.
        :param y: Pixel Y position.
        :return: Point on map in absolute units.
        """
        nx = self.offset_x + (x - (self.width() / 2)) / self.zoom
        ny = self.offset_y - (y - (self.height() / 2)) / self.zoom
        return Point(nx, ny)

    def in_radius(self, origin: Point, pt: Point, radius: float) -> bool:
        """Returns whether pt is in radius from origin."""
        dx = pt.x - origin.x
        dy = pt.y - origin.y
        return (dx * dx + dy * dy) <= radius * radius


class MainWindow(QMainWindow):
    """
    Start's up a FactoryWorker, which in turn starts a FactoryAgent and then all other agents. FactoryWorker updates
    ViewModel from which MainWindow (Canvas) then reads data.
    """

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        # Agent
        self.factory_agent = FactoryAgent(f"{settings.AGENT_NAMES['factory']}@{settings.HOST}", settings.PASSWORD)
        self.factory_worker = None
        self.view_model = ViewModel(self.set_description_text)

        # UI
        self.canvas = None
        self._description = None
        self._start_btn = None
        self.init_ui()

        # Multithreading
        self.thread_pool = QThreadPool()
        print("Multithreading with maximum %d threads" % self.thread_pool.maxThreadCount())

        # Redraw scene every 100ms
        self.timer = QTimer()
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.recurring_timer)

        # Start
        self.show()
        self.timer.start()

    def init_ui(self):
        self.setWindowTitle("Industry 4.0")

        # Layout
        main_layout = QHBoxLayout()
        side_layout = QVBoxLayout()

        # Controls
        self.canvas = Canvas(self.view_model)
        main_layout.addWidget(self.canvas)

        self._start_btn = QPushButton("Start worker")
        self._start_btn.pressed.connect(self.start_agent_worker)
        self._start_btn.setFixedWidth(300)
        side_layout.addWidget(self._start_btn)

        self._description = QLabel()
        self._description.setFixedWidth(300)
        self._description.setAlignment(Qt.AlignTop)
        side_layout.addWidget(self._description)
        self.view_model.set_description_text("click on the map to\nhide this agent placeholder\na bad description")

        main_layout.addLayout(side_layout, 100)

        w = QWidget()
        w.setLayout(main_layout)
        self.setCentralWidget(w)

    def set_description_text(self, text: str) -> None:
        self._description.setText(text)

    def update_tr_position_fn(self, tr_jid: str, pos) -> None:
        """

        :param tr_jid:
        :param pos:
        """
        self.view_model.tr_map[tr_jid] = pos

    def update_view_model_fn(self, tr_list, tr_map, factory_map):
        """

        :param tr_list:
        :param tr_map:
        :param factory_map:
        """
        if tr_list:
            self.view_model.tr_list = tr_list
        if tr_map:
            self.view_model.tr_map = tr_map
        if factory_map:
            self.view_model.factory_map = factory_map

    def execute_agent(self, update_tr_position_callback, update_view_model_callback):
        agent = self.factory_agent
        agent.set_update_callbacks(update_tr_position_callback, update_view_model_callback)
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
        self._start_btn.setEnabled(True)

    def start_agent_worker(self) -> None:
        """Binds defined signals, then starts factory agent in separate thread."""
        try:
            # Pass the function to execute
            self.factory_worker = Worker(self.execute_agent)  # Any other args, kwargs are passed to the run function
            self.factory_worker.signals.result.connect(self.process_result)
            self.factory_worker.signals.finished.connect(self.thread_complete)
            self.factory_worker.signals.update_tr_position.connect(self.update_tr_position_fn)
            self.factory_worker.signals.update_view_model.connect(self.update_view_model_fn)

            # Execute
            self.thread_pool.start(self.factory_worker)
            self._start_btn.setEnabled(False)
        except Exception as e:
            print(repr(e))

    def recurring_timer(self) -> None:
        self.canvas.draw_scene()


if __name__ == '__main__':
    app = QApplication([])
    window = MainWindow()

    # app.exec()  # TODO
    app.exec_()
    # sys.exit(app.exec_())
