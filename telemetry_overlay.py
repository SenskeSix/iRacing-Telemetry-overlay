import sys
import numpy as np
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QTimer, Qt, QRect
from PyQt5.QtGui import QColor, QPainter, QBrush, QCursor
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import irsdk

class IRacingTelemetry:
    def __init__(self):
        self.ir = irsdk.IRSDK()
        self.ir.startup()
        self.history_length = 200
        self.reset_data()

    def reset_data(self):
        self.throttle = np.zeros(self.history_length)
        self.brake = np.zeros(self.history_length)
        self.steer = np.zeros(self.history_length)
        self.speed = np.zeros(self.history_length)
        self.gear = np.zeros(self.history_length)
        self.distance = np.zeros(self.history_length)  # Track distance traveled in meters
        self.time = np.zeros(self.history_length)

    def update(self):
        if not self.ir.is_connected:
            self.reset_data()
        else:
            # Shift old data and add new values
            self.throttle = np.roll(self.throttle, -1)
            self.brake = np.roll(self.brake, -1)
            self.steer = np.roll(self.steer, -1)
            self.speed = np.roll(self.speed, -1)
            self.gear = np.roll(self.gear, -1)
            self.distance = np.roll(self.distance, -1)
            self.time = np.roll(self.time, -1)

            # Update with new telemetry data
            self.throttle[-1] = self.ir['Throttle']
            self.brake[-1] = self.ir['Brake']
            self.steer[-1] = self.ir['Steer']  # Steering data ranges from -1 (left) to 1 (right)
            self.speed[-1] = self.ir['Speed']  # Speed in meters per second
            self.gear[-1] = self.ir['Gear']
            self.time[-1] = self.ir['SessionTime']

            # Calculate distance traveled in meters (speed * time delta)
            if len(self.time) > 1:
                time_delta = self.time[-1] - self.time[-2]
                if self.speed[-1] > 0:  # Only update distance if the car is moving
                    self.distance[-1] = self.distance[-2] + (self.speed[-1] * time_delta)
                else:
                    self.distance[-1] = self.distance[-2]  # Keep distance constant when stationary

class ApplicationWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("iRacing Telemetry Overlay")
        self.setGeometry(100, 100, 450, 150)  # Smaller default window size with 1:3 aspect ratio
        self.setAttribute(Qt.WA_TranslucentBackground)  # Enable transparent background
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)  # Remove window border and keep on top

        self.main_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.main_widget)
        layout = QtWidgets.QVBoxLayout(self.main_widget)
        layout.setContentsMargins(5, 0, 5, 0)  # Add tiny transparent margins on the sides

        # Horizontal layout for close button and dropdown
        top_layout = QtWidgets.QHBoxLayout()
        top_layout.setAlignment(Qt.AlignLeft)
        top_layout.setContentsMargins(50, 5, 5, 5)  # Shift close button and dropdown to the right

        # Close button (small cross in the corner)
        self.close_button = QtWidgets.QPushButton("×")
        self.close_button.setFixedSize(20, 20)
        self.close_button.setStyleSheet("background-color: transparent; color: white; font-size: 16px; border: none;")
        self.close_button.clicked.connect(self.close)
        top_layout.addWidget(self.close_button)

        # Dropdown button for telemetry options
        self.dropdown_button = QtWidgets.QPushButton("Telemetry Options")
        self.dropdown_button.setFixedWidth(120)  # Set a fixed width for the dropdown button
        self.dropdown_button.setStyleSheet("background-color: rgba(50, 50, 50, 0.7); color: white;")
        self.dropdown_button.clicked.connect(self.show_dropdown_menu)  # Connect to dropdown menu
        top_layout.addWidget(self.dropdown_button)

        layout.addLayout(top_layout)

        # Create a menu for the dropdown button
        self.dropdown_menu = QtWidgets.QMenu(self)
        self.dropdown_button.setMenu(self.dropdown_menu)

        # Checkboxes for telemetry options
        self.throttle_checkbox = QtWidgets.QCheckBox("Throttle (Lime)")
        self.brake_checkbox = QtWidgets.QCheckBox("Brake (Red)")
        self.steer_checkbox = QtWidgets.QCheckBox("Steer (Cyan)")
        self.speed_checkbox = QtWidgets.QCheckBox("Speed (Yellow)")
        self.gear_checkbox = QtWidgets.QCheckBox("Gear (Magenta)")

        # Set default checked states
        self.throttle_checkbox.setChecked(True)
        self.brake_checkbox.setChecked(True)
        self.steer_checkbox.setChecked(True)
        self.speed_checkbox.setChecked(True)
        self.gear_checkbox.setChecked(True)

        # Create QAction objects for each checkbox and add them to the menu
        self.throttle_action = QtWidgets.QWidgetAction(self.dropdown_menu)
        self.throttle_action.setDefaultWidget(self.throttle_checkbox)
        self.dropdown_menu.addAction(self.throttle_action)

        self.brake_action = QtWidgets.QWidgetAction(self.dropdown_menu)
        self.brake_action.setDefaultWidget(self.brake_checkbox)
        self.dropdown_menu.addAction(self.brake_action)

        self.steer_action = QtWidgets.QWidgetAction(self.dropdown_menu)
        self.steer_action.setDefaultWidget(self.steer_checkbox)
        self.dropdown_menu.addAction(self.steer_action)

        self.speed_action = QtWidgets.QWidgetAction(self.dropdown_menu)
        self.speed_action.setDefaultWidget(self.speed_checkbox)
        self.dropdown_menu.addAction(self.speed_action)

        self.gear_action = QtWidgets.QWidgetAction(self.dropdown_menu)
        self.gear_action.setDefaultWidget(self.gear_checkbox)
        self.dropdown_menu.addAction(self.gear_action)

        self.figure = Figure(facecolor='none')  # Transparent figure background
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background-color: transparent;")  # Transparent canvas background
        layout.addWidget(self.canvas)

        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor((0.1, 0.1, 0.1, 0.25))  # Dark greyish-black with 25% transparency
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['bottom'].set_visible(False)
        self.ax.spines['left'].set_visible(False)
        self.ax.tick_params(colors='white', labelsize=6)  # Smaller x-axis labels
        self.ax.set_yticklabels([])  # Remove y-axis labels
        self.ax.set_xlabel("Distance (m)", color='white', fontsize=8)  # Add x-axis label

        # Add padding to prevent x-axis labels from being cut off
        self.figure.subplots_adjust(bottom=0.2)

        self.telemetry = IRacingTelemetry()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(100)  # Update every 100 ms

        # Variables for window dragging and resizing
        self.dragging = False
        self.drag_position = QtCore.QPoint()
        self.resizing = False
        self.resize_edge = None
        self.resize_margin = 10  # Margin for detecting resize area

    def show_dropdown_menu(self):
        """Show the dropdown menu when the button is clicked."""
        self.dropdown_menu.exec_(self.dropdown_button.mapToGlobal(QtCore.QPoint(0, self.dropdown_button.height())))

    def update_plot(self):
        self.telemetry.update()
        self.ax.clear()
        self.ax.set_facecolor((0.1, 0.1, 0.1, 0.25))  # Ensure plot background remains dark greyish-black
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['bottom'].set_visible(False)
        self.ax.spines['left'].set_visible(False)
        self.ax.tick_params(colors='white', labelsize=6)  # Smaller x-axis labels
        self.ax.set_yticklabels([])  # Remove y-axis labels
        self.ax.set_xlabel("Distance (m)", color='white', fontsize=8)  # Add x-axis label

        # Plot selected telemetry options
        if self.throttle_checkbox.isChecked():
            self.ax.plot(self.telemetry.distance, self.telemetry.throttle, color='lime', linewidth=2)
        if self.brake_checkbox.isChecked():
            self.ax.plot(self.telemetry.distance, self.telemetry.brake, color='red', linewidth=2)
        if self.steer_checkbox.isChecked():
            # Normalize steering data to oscillate around 0.5 (middle of the graph)
            steer_normalized = (self.telemetry.steer + 1) * 0.5  # Scale from [-1, 1] to [0, 1]
            self.ax.plot(self.telemetry.distance, steer_normalized, color='cyan', linewidth=2)
        if self.speed_checkbox.isChecked():
            # Normalize speed data to a range of [0, 1] (assuming max speed is 83.33 m/s ≈ 300 km/h)
            speed_normalized = self.telemetry.speed / 83.33  # Scale to [0, 1]
            self.ax.plot(self.telemetry.distance, speed_normalized, color='yellow', linewidth=2)
        if self.gear_checkbox.isChecked():
            # Normalize gear data to a range of [0, 1] (assuming max gear is 6)
            gear_normalized = self.telemetry.gear / 6.0  # Scale to [0, 1]
            self.ax.plot(self.telemetry.distance, gear_normalized, color='magenta', linewidth=2)

        # Adjust x-axis limits to show 300 meters of data
        if self.telemetry.distance[-1] > 150:  # Scroll after 150 meters (50% of 300 meters)
            self.ax.set_xlim(self.telemetry.distance[-1] - 150, self.telemetry.distance[-1] + 150)
        else:
            self.ax.set_xlim(0, 300)  # Initial view

        self.canvas.draw()

    def paintEvent(self, event):
        # Add a blur effect and semi-transparent background
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor(50, 50, 50, 64)))  # Greyish-black with 25% transparency
        painter.setPen(Qt.NoPen)
        painter.drawRect(self.rect())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Check if the mouse is near the edges for resizing
            self.resize_edge = self.get_resize_edge(event.pos())
            if self.resize_edge:
                self.resizing = True
            else:
                # Otherwise, start dragging
                self.dragging = True
                self.drag_position = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(event.globalPos() - self.drag_position)
        elif self.resizing:
            self.resize_window(event)
        else:
            # Change cursor when near the edges
            edge = self.get_resize_edge(event.pos())
            if edge:
                if edge in ["left", "right"]:
                    self.setCursor(Qt.SizeHorCursor)
                elif edge in ["top", "bottom"]:
                    self.setCursor(Qt.SizeVerCursor)
            else:
                self.setCursor(Qt.ArrowCursor)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            self.resizing = False
            self.resize_edge = None
            self.setCursor(Qt.ArrowCursor)

    def get_resize_edge(self, pos):
        rect = self.rect()
        if pos.x() <= self.resize_margin:
            return "left"
        elif pos.x() >= rect.width() - self.resize_margin:
            return "right"
        elif pos.y() <= self.resize_margin:
            return "top"
        elif pos.y() >= rect.height() - self.resize_margin:
            return "bottom"
        return None

    def resize_window(self, event):
        rect = self.rect()
        global_pos = event.globalPos()
        if self.resize_edge == "left":
            new_width = rect.width() - (global_pos.x() - self.x())
            if new_width > self.minimumWidth():
                self.setGeometry(global_pos.x(), self.y(), new_width, self.height())
        elif self.resize_edge == "right":
            new_width = global_pos.x() - self.x()
            if new_width > self.minimumWidth():
                self.resize(new_width, self.height())
        elif self.resize_edge == "top":
            new_height = rect.height() - (global_pos.y() - self.y())
            if new_height > self.minimumHeight():
                self.setGeometry(self.x(), global_pos.y(), self.width(), new_height)
        elif self.resize_edge == "bottom":
            new_height = global_pos.y() - self.y()
            if new_height > self.minimumHeight():
                self.resize(self.width(), new_height)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle('Fusion')  # Use a modern style
    window = ApplicationWindow()
    window.show()
    sys.exit(app.exec_())
