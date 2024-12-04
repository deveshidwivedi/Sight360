import sys
import cv2
import yolo
import time
import path_finding as pf
import midas_single_image as midas
import socket
import threading
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QPushButton, QListWidgetItem, QPlainTextEdit,QCheckBox, QSizePolicy
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer, Qt,QThread,pyqtSignal
import blip
import deepface_recognizer as deepface
from ElevenLabs.eleven_labs import play_audio
import numpy as np
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
from playsound import playsound

PORT = 5050
SERVER= socket.gethostbyname(socket.gethostname())
ADDR = (SERVER, PORT)
HEADER = 64
FORMAT = 'utf-8'
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(ADDR)

def create_tracker():
    tracker = cv2.TrackerKCF_create()
    return tracker

class WifiThread(QThread):
    finished= pyqtSignal()

    def __init__(self, wifi_control, parent=None):
        super().__init__(parent)
        self.wifi_control= wifi_control

    def run(self):
        self.wifi_control()
     

def get_bounding_box(frame, objects, locations, index):
    xmin, ymin, xmax, ymax = [int(v) for v in locations[index]]
    return (xmin, ymin, xmax - xmin, ymax - ymin)

class VideoWidget(QWidget):
    def __init__(self):

        super().__init__()
        self.action = 1
        self.yolo_model = yolo.load_yolo()
        self.blip_processor, self.blip_model = blip.setup_model()
        self.tracker = create_tracker()
        self.video = cv2.VideoCapture(2)
        self.frame = None
        self.raw_frame = None
        self.objects = []
        self.locations = []
        self.bbox = None
        self.tracking = False
        self.tracked_objects = {}
        self.recent_objects = {}
        self.navigation_started = False
        self.model, self.transform, self.net_w, self.net_h, self.device = midas.init()

        self.video_label = QLabel(self)
        self.objects_list = QListWidget(self)
        self.recent_objects_list = QListWidget(self)
        self.back_button = QPushButton("Back to YOLO mode", self)
        self.navigate_button = QPushButton("Navigate", self)
        self.navigate_button.hide()
        self.caption_textbox = QPlainTextEdit(self)
        self.caption_textbox.setReadOnly(True)
        self.describe_button = QPushButton("Describe environment", self)
        self.facerecognize_button = QPushButton("Recognize face", self)
        self.faceinfer_button = QPushButton("Infer face", self)
        self.face_textbox = QPlainTextEdit(self)
        self.face_textbox.setReadOnly(True)
        self.fps_graph = PlotWidget(self)
        self.fps_graph.setYRange(0, 60)  

        self.fps_data=[]
        self.max_fps_data_points = 100

        self.current_time = 0
        self.last_played_time = 0


        


        video_layout = QVBoxLayout()
        video_layout.addWidget(self.video_label)
        video_layout.addWidget(self.objects_list)
        video_layout.addWidget(self.back_button)
        video_layout.addWidget(self.navigate_button)
        video_layout.addWidget(self.describe_button)
        video_layout.addWidget(self.caption_textbox)
        video_layout.addWidget(self.facerecognize_button)
        video_layout.addWidget(self.faceinfer_button)
        video_layout.addWidget(self.face_textbox)
        self.wifi_checkbox = QCheckBox("Wifi", self)
        video_layout.addWidget(self.wifi_checkbox)
        video_layout.addWidget(self.fps_graph)

        sidebar_layout = QVBoxLayout()
        sidebar_layout.addWidget(QLabel("Recently appeared objects:"))
        sidebar_layout.addWidget(self.recent_objects_list)

        main_layout = QHBoxLayout()
        main_layout.addLayout(video_layout)
        main_layout.addLayout(sidebar_layout)
        self.setLayout(main_layout)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_video)
        self.timer.start(30)

        self.recent_objects_timer = QTimer()
        self.recent_objects_timer.timeout.connect(self.update_recent_objects)
        self.recent_objects_timer.start(3000)

        self.recent_objects_list.itemClicked.connect(self.start_tracking)
        self.back_button.clicked.connect(self.switch_to_yolo_mode)
        self.navigate_button.clicked.connect(self.toggle_navigation)
        self.describe_button.clicked.connect(self.describe_environment)
        self.facerecognize_button.clicked.connect(self.recognize_face)
        self.faceinfer_button.clicked.connect(self.infer_face)
        self.wifi_checkbox.stateChanged.connect(self.toggle_wifi_thread)

    def update_fps_graph(self, fps):
        self.fps_data.append(fps)
        if len(self.fps_data) > self.max_fps_data_points:
            self.fps_data.pop(0)
        self.fps_graph.clear()
        self.fps_graph.plot(self.fps_data, pen=pg.mkPen(color=(255, 0, 0), width=2))

    def update_video(self):
        t1=time.time()
        ret, self.frame = self.video.read()
        if ret:
            self.raw_frame = self.frame.copy()
            if not self.tracking:
                result = yolo.inference(self.frame, model=self.yolo_model)
                self.frame = result[2]
                self.objects = result[0]
                self.locations = result[1]

                self.objects_list.clear()
                for obj in self.objects:
                    item = QListWidgetItem(obj)
                    self.objects_list.addItem(item)

                for obj_name, bbox in self.tracked_objects.items():
                    if obj_name in self.objects:
                        index = self.objects.index(obj_name)
                        self.bbox = get_bounding_box(self.frame, self.objects, self.locations, index)
                        self.tracker = create_tracker()
                        self.tracker.init(self.frame, self.bbox)
                        self.tracking = True
                        self.navigate_button.show()
                        break

            else:
                success, self.bbox = self.tracker.update(self.frame)

                if success:
                    x, y, w, h = [int(v) for v in self.bbox]
                    cv2.rectangle(self.frame, (x, y), (x + w, y + h), (0,255, 0), 2)
                    if self.navigation_started:
                        self.start_navigation()
                else:
                    self.switch_to_yolo_mode()
            t2 = time.time()
            fps = 1/(t2-t1)
            if fps > 60:
                fps = 60
        
            self.update_fps_graph(fps)

           
            cv2.putText(self.frame,"FPS: "+str(int(fps)),(10,30),cv2.FONT_HERSHEY_SIMPLEX,1,(0,0,255),2)

            n = 1.3
            self.frame = cv2.resize(self.frame, (int(self.frame.shape[1] * n), int(self.frame.shape[0] * n)))

            height, width, channel = self.frame.shape
            bytes_per_line = 3 * width
            qimage = QImage(self.frame.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
            self.video_label.setPixmap(QPixmap.fromImage(qimage))
    def toggle_wifi_thread(self,state):
        if state:
            self.wifi_thread = WifiThread(self.wifi_control)
            self.wifi_thread.start()
        else:
            self.wifi_thread.quit()
    def wifi_control(self):
        
        s.listen()
        while self.wifi_checkbox.isChecked():
            conn, addr = s.accept()
            thread = threading.Thread(target=self.handle_client, args=(conn, addr))
            thread.start()
    
            if thread.join() == 0:
                break
            print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")

    def handle_client(self,conn, addr):
        print(f"[NEW CONNECTION] {addr} connected.")
        connected = True
        while connected:
            msg_length = conn.recv(HEADER).decode(FORMAT)
            print(msg_length)
            parsed = msg_length.split(" ")
            val = parsed[1][1:]
            if msg_length:
                print(f"[{addr}] {val}")
                if val== 'env':
                    print(f"[{addr}] {msg_length} env desc")
                    self.describe_environment()
                if val== 'Face':
                    print(f"[{addr}] {msg_length} face infer")
                    self.infer_face()
                if val== 'Ai':
                    print(f"[{addr}] {msg_length}")
                    self.recognize_face()
                if val== 'nav':
                    print(f"[{addr}] {msg_length}")
                    self.toggle_navigation()
                    if self.navigation_started:
                        self.start_navigation()
                if val== 'Disconnect':
                    connected = False
                    print(f"[{addr}] {msg_length}")
                    print("Disconnected")
                    conn.close()
                    break
                else:
                    print(f"[{addr}] {msg_length}")
                    self.start_tracking(val)
        return 0


    def update_recent_objects(self):
        current_time = time.time()
        for obj in self.objects:
            if obj not in self.recent_objects:
                self.recent_objects[obj] = current_time

        expired_objects = [obj for obj, timestamp in self.recent_objects.items() if current_time - timestamp > 30]
        for obj in expired_objects:
            del self.recent_objects[obj]

        self.recent_objects_list.clear()
        for obj in self.recent_objects:
            item = QListWidgetItem(obj)
            if obj in self.tracked_objects:
                item.setBackground(Qt.green)
            self.recent_objects_list.addItem(item)

    def start_tracking(self, item):
        try:
            obj_name = item.text()
        except:
            obj_name = item

        if obj_name in self.tracked_objects:
            del self.tracked_objects[obj_name]
            item.setBackground(Qt.white)
            self.navigate_button.hide()
        else:
            self.tracked_objects[obj_name] = None
            item.setBackground(Qt.green)
            if self.tracking:
                self.navigate_button.show()

    def switch_to_yolo_mode(self):
        self.tracking = False
        self.navigate_button.hide()

    def toggle_navigation(self):
        self.navigation_started = not self.navigation_started
        if self.navigation_started:
            self.navigate_button.setText("Navigating...")
            # set button color
            self.navigate_button.setStyleSheet("background-color: green")

        else:
            self.navigate_button.setText("Navigate")
            # set button color
            self.navigate_button.setStyleSheet("background-color: white")

    def recognize_face(self):
        if self.frame is not None:
            # Convert the frame to an RGB image
            image = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)

            # Generate the caption using the Blip model
            name, x, y, w, h = deepface.recognize_face(image)

            # Display the caption in the text box
            self.face_textbox.setPlainText(name)
            play_audio(name)

    def infer_face(self):
        if self.frame is not None:
            # Convert the frame to an RGB image
            image = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)

            age,gender,race,emotion = deepface.infer(image)
            # concat the attributes
            inference_result = f"age: {age}, gender: {gender}, race: {race}, emotion: {emotion}"
            # Display the caption in the text box
            self.face_textbox.setPlainText(inference_result)
            play_audio(inference_result)

    def describe_environment(self):
        if self.frame is not None:
            # Convert the frame to an RGB image
            image = cv2.cvtColor(self.raw_frame, cv2.COLOR_BGR2RGB)
            caption_text = blip.caption(image,processor = self.blip_processor,model = self.blip_model)
            self.caption_textbox.setPlainText(caption_text)
            play_audio(caption_text)

    def moving_average_smoothing(self,path, window_size=5):
        smoothed_path = []
        for i in range(len(path)):
            start = max(0, i - window_size // 2)
            end = min(len(path), i + window_size // 2 + 1)
            avg_point = np.mean(path[start:end], axis=0).astype(int)
            smoothed_path.append(avg_point)
        return smoothed_path


    def angle_between_vectors(self,v1, v2):
        dot_product = np.dot(v1, v2)
        magnitude_product = np.linalg.norm(v1) * np.linalg.norm(v2)
        angle = np.arccos(dot_product / magnitude_product) * (180 / np.pi)
        return angle

    def direction_from_angle(self,angle, threshold=30):
        if angle < -threshold:
            return "left"
        elif angle > threshold:
            return "right"
        else:
            return "forward"

    def start_navigation(self):
        direction = ''
        if self.tracking and self.bbox:
            x, y, w, h = [int(v) for v in self.bbox]
            target_point = (x + w // 2, y + h)
            cv2.circle(self.frame, target_point, 5, (0, 0, 255), -1)

            save_path = './Midas/inputs/rgb/'
            cv2.imwrite(save_path + 'frame_gui.png', self.raw_frame)
            midas.run_midas(save_path, self.model, self.transform, self.net_w, self.net_h, self.device)
            depth_map = midas._open_map()
            path_result = pf.path_to_point(target_point, depth_map)

        if path_result is None:
            print('No path found')
        else:
            path = path_result[0]
            depth_map_with_path = path_result[1]

            # Smooth the path using moving average
            smoothed_path = self.moving_average_smoothing(path)

            # Draw the smoothed path on the frame
            for i in range(len(smoothed_path) - 1):
                cv2.line(self.frame, tuple(smoothed_path[i]), tuple(smoothed_path[i + 1]), (0, 0, 255), 2)

            # calculate the distance left on the path
            distance_left = pf.distance_left(smoothed_path)
            if distance_left < 70:
                direction = 'stop'
            if not (direction == 'stop'):

                scaled_distance_left = distance_left
                # add the distance left to the navigation button
                self.navigate_button.setText(f'Navigating... ({distance_left:.2f} px)')

                # Calculate the direction of the nearest portion of the smoothed path
                origin = np.array([self.frame.shape[1] // 2, self.frame.shape[0]])
                try:
                    nearest_point = np.array(smoothed_path[2])
                except IndexError:
                    print('At the end of the path')
                    direction = 'stop'
                    nearest_point = np.array(smoothed_path[0])

                forward_direction = np.array([0, -1])  # Assuming the user is facing up in the frame
                path_direction = nearest_point - origin

                angle = self.angle_between_vectors(forward_direction, path_direction)
                cross_product = np.cross(forward_direction, path_direction)
                signed_angle = angle if cross_product >= 0 else -angle


                direction = self.direction_from_angle(signed_angle) 

            print(f'direction: {direction}')

            # Display the direction on the frame
            if direction:
                cv2.putText(self.frame, direction.upper(), (origin[0] - 50, origin[1] - 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
                
            # Play the appropriate sound file based on the direction every 2 seconds
            self.current_time = time.time()
            if self.current_time - self.last_played_time >= 2:
                if direction == 'left':
                    playsound('left.mp3')
                elif direction == 'right':
                    playsound('right.mp3')
                elif direction == 'forward':
                    playsound('forward.mp3')
                elif direction == 'stop':
                    playsound('stop.mp3')
                    self.toggle_navigation()
                self.last_played_time = self.current_time


            cv2.imshow('Depth Map', depth_map_with_path)
            


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VideoWidget()
    window.show()
    sys.exit(app.exec_())
