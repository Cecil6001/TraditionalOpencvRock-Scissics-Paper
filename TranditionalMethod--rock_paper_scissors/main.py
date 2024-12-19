from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QFrame, QComboBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap
import cv2
import sys
from game_logic import GameLogic, GameState
from hand_recognition import HandRecognition
import time


class GameWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("石头剪刀布游戏")

        # 初始化手势识别模块
        self.hand_recognition = HandRecognition()

        # 初始化游戏逻辑
        self.game_logic = GameLogic()

        # 游戏设置
        self.game_mode = "normal"  # normal, always_win, always_lose
        self.rounds_setting = 1  # 1, 3, 5
        self.is_playing = False
        self.last_gesture_time = 0
        self.gesture_timeout = 2.0  # 出手时间限制（秒）
        self.round_paused = False  # 新增：回合暂停状态

        # 添加新的属性
        self.current_gesture = None  # 当前识别到的手势
        self.round_confirmed = False  # 是否确认本���结果

        # 加载手势图片
        self.gesture_images = self._load_gesture_images()

        # 修改游戏模式名称
        self.mode_names = ["普通模式", "电脑永远赢", "电脑永远输"]

        # 初始化UI
        self._init_ui()
        # 初始化摄像头
        self.camera = cv2.VideoCapture(0)
        self.timer = QTimer()
        self.timer.timeout.connect(self.process_frame)
        self.timer.start(30)  # 30ms刷新率

    def _init_ui(self):
        """初始化UI界面"""
        # 设置主窗口样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QLabel {
                color: #333333;
                font-size: 16px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 16px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QComboBox {
                padding: 5px;
                border: 1px solid #999;
                border-radius: 3px;
                min-width: 150px;
            }
        """)

        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 创建摄像头显示区域
        self.camera_label = QLabel()
        self.camera_label.setFixedSize(640, 480)
        self.camera_label.setStyleSheet("border: 2px solid #cccccc; border-radius: 10px;")
        main_layout.addWidget(self.camera_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # 创建游戏信息显示区域
        info_layout = QHBoxLayout()

        # 玩家信息区域
        self.player_frame = self._create_player_frame("玩家")
        self.player_gesture_label = self.player_frame.findChild(QLabel, "gesture_label")
        info_layout.addWidget(self.player_frame)

        # 比分显示
        score_frame = QFrame()
        score_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                padding: 10px;
            }
            QLabel {
                font-size: 18px;
                font-weight: bold;
            }
        """)
        score_layout = QVBoxLayout(score_frame)

        self.score_label = QLabel("比分: 0 - 0")
        self.result_label = QLabel("准备开始")
        self.time_label = QLabel("剩余时间: --")

        score_layout.addWidget(self.score_label, alignment=Qt.AlignmentFlag.AlignCenter)
        score_layout.addWidget(self.result_label, alignment=Qt.AlignmentFlag.AlignCenter)
        score_layout.addWidget(self.time_label, alignment=Qt.AlignmentFlag.AlignCenter)

        info_layout.addWidget(score_frame)

        # 电脑信息区域
        self.computer_frame = self._create_player_frame("电脑")
        self.computer_gesture_label = self.computer_frame.findChild(QLabel, "gesture_label")
        info_layout.addWidget(self.computer_frame)

        main_layout.addLayout(info_layout)

        # 创建控制按钮区域
        control_layout = QHBoxLayout()
        self._create_control_buttons(control_layout)
        main_layout.addLayout(control_layout)

        # 设置窗口大小
        self.setMinimumSize(800, 700)

    def _create_player_frame(self, title):
        """创建玩家信息框"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        layout = QVBoxLayout(frame)

        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # 添加图片显示标签
        image_label = QLabel()
        image_label.setObjectName("image_label")
        image_label.setFixedSize(100, 100)  # 设置固定大小
        image_label.setScaledContents(True)  # 图片自适应大小
        layout.addWidget(image_label)

        gesture_label = QLabel("等待出手...")
        gesture_label.setObjectName("gesture_label")
        gesture_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(gesture_label)

        return frame

    def _create_control_buttons(self, layout):
        """创建控制按钮"""
        try:
            # 游戏模式选择
            mode_layout = QVBoxLayout()
            mode_label = QLabel("游戏模式:")
            self.mode_combo = QComboBox()
            self.mode_combo.addItems(self.mode_names)
            self.mode_combo.currentIndexChanged.connect(self._change_game_mode)
            mode_layout.addWidget(mode_label)
            mode_layout.addWidget(self.mode_combo)

            # 回合数选择
            rounds_layout = QVBoxLayout()
            rounds_label = QLabel("游戏轮数:")
            self.rounds_combo = QComboBox()
            self.rounds_combo.addItems(["一局定胜负", "三局两胜", "五局三胜"])
            self.rounds_combo.currentIndexChanged.connect(self._change_rounds)
            rounds_layout.addWidget(rounds_label)
            rounds_layout.addWidget(self.rounds_combo)

            # 按钮布局
            button_layout = QVBoxLayout()

            # 开始按钮
            start_button = QPushButton("开始新游戏")
            start_button.clicked.connect(self.start_new_game)
            button_layout.addWidget(start_button)

            # 确认按钮
            confirm_button = QPushButton("确认本轮")
            confirm_button.clicked.connect(self._confirm_round)
            button_layout.addWidget(confirm_button)

            # 跳过等待按钮
            skip_button = QPushButton("跳过等待")
            skip_button.clicked.connect(self._skip_waiting)
            button_layout.addWidget(skip_button)

            # 添加到主布局
            layout.addLayout(mode_layout)
            layout.addLayout(rounds_layout)
            layout.addLayout(button_layout)

        except Exception as e:
            print(f"Error in _create_control_buttons: {e}")

    def process_frame(self):
        """处理摄像头帧"""
        try:
            ret, frame = self.camera.read()
            if not ret:
                return

            # 手势识别
            frame, gestures = self.hand_recognition.detect_gestures(frame)

            # 游戏进行中且检测到手势且不在暂停状态
            if self.is_playing and gestures and not self.round_confirmed and not self.round_paused:
                current_time = time.time()
                elapsed_time = current_time - self.last_gesture_time

                # 更新剩余时间显示
                remaining_time = max(0, self.gesture_timeout - elapsed_time)
                self.time_label.setText(f"剩余时间: {remaining_time:.1f}s")

                # 检查是否超时
                if elapsed_time > self.gesture_timeout:
                    self.round_paused = True  # 暂停回合
                    self.current_gesture = gestures[0]
                    self._judge_round()  # 判定本回合结果
                    return

                # 更新当前手势
                self.current_gesture = gestures[0]
                self._update_player_display(self.current_gesture)

            # 更新摄像头画面
            self.update_camera_display(frame)

        except Exception as e:
            print(f"Error in process_frame: {e}")

    def update_camera_display(self, frame):
        """更新摄像头画面显示"""
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        self.camera_label.setPixmap(pixmap.scaled(
            self.camera_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))

    def _update_player_display(self, gesture):
        """更新玩家手势显示"""
        try:
            # 更新文字显示
            self.player_gesture_label.setText(f"手势: {self._translate_gesture(gesture)}")

            # 更新图片显示
            image_label = self.player_frame.findChild(QLabel, "image_label")
            if image_label and gesture in self.gesture_images:
                image_label.setPixmap(self.gesture_images[gesture])

        except Exception as e:
            print(f"Error updating player display: {e}")

    def _update_computer_display(self, gesture):
        """更新电脑手势显示"""
        try:
            # 更新文字显示
            self.computer_gesture_label.setText(f"手势: {self._translate_gesture(gesture)}")

            # 更新图片显示
            image_label = self.computer_frame.findChild(QLabel, "image_label")
            if image_label and gesture in self.gesture_images:
                image_label.setPixmap(self.gesture_images[gesture])

        except Exception as e:
            print(f"Error updating computer display: {e}")

    def _judge_round(self):
        """判定回合结果"""
        try:
            if self.current_gesture == "unknown":
                self.result_label.setText("手势无法识别，请重新开始回合")
                return

            # 获取电脑手势
            if self.game_mode == "always_win":
                computer_gesture = self.game_logic.get_winning_move(self.current_gesture)
            elif self.game_mode == "always_lose":
                computer_gesture = self.game_logic.get_losing_move(self.current_gesture)
            else:
                computer_gesture = self.game_logic.get_random_move()

            # 更新显示
            self._update_computer_display(computer_gesture)

            # 判断胜负
            result = self.game_logic.judge_round(self.current_gesture, computer_gesture)

            if "平局" in result["message"]:
                # 平局时重置回合状态
                self.round_paused = False
                self.round_confirmed = False
                self.current_gesture = None
                self.last_gesture_time = time.time()
                self.result_label.setText("平局！请重新出手")
                self.time_label.setText(f"剩余时间: {self.gesture_timeout:.1f}s")
            else:
                self.result_label.setText(f"{result['message']} (请点击确认本轮继续)")
                self.score_label.setText(f"比分: {result['score']}")

            # 检查游戏是否结束
            if result["game_over"]:
                self.is_playing = False
                winner = result["winner"]
                if winner == "玩家":
                    self.result_label.setText("恭喜你获得胜利！🎉")
                else:
                    self.result_label.setText("再接再厉！💪")

        except Exception as e:
            print(f"Error in judge round: {e}")

    def _confirm_round(self):
        """确认本轮结果并继续下一轮"""
        try:
            if not self.is_playing and not self.round_paused:
                return

            # 重置回合状态
            self.round_paused = False
            self.round_confirmed = False
            self.current_gesture = None
            self.last_gesture_time = time.time()

            if not self.game_logic.game_state.is_game_over():
                self.result_label.setText("新回合开始！")
                self.time_label.setText(f"剩余时间: {self.gesture_timeout:.1f}s")
                self.player_gesture_label.setText("等待出手...")
                self.computer_gesture_label.setText("等待出手...")

                # 清空手势图片
                for frame in [self.player_frame, self.computer_frame]:
                    image_label = frame.findChild(QLabel, "image_label")
                    if image_label:
                        image_label.clear()

        except Exception as e:
            print(f"Error in confirm round: {e}")

    def _skip_waiting(self):
        """跳过等待时间"""
        try:
            if self.is_playing and not self.round_paused:
                # 设置时间为超时状态
                self.last_gesture_time = time.time() - self.gesture_timeout - 0.1

                if self.current_gesture:  # 如果已经识别到手势
                    self.round_paused = True
                    self._judge_round()
                else:
                    self.result_label.setText("请先做出手势！")
        except Exception as e:
            print(f"Error in skip_waiting: {e}")

    def _translate_gesture(self, gesture):
        """将手势翻译为中文"""
        translations = {
            "rock": "石头",
            "paper": "布",
            "scissors": "剪刀",
            "unknown": "未知"
        }
        return translations.get(gesture, gesture)

    def _change_game_mode(self, index):
        """更改游戏模式"""
        try:
            modes = ["normal", "always_win", "always_lose"]
            self.game_mode = modes[index]
            self.result_label.setText(f"已切换到{self.mode_combo.currentText()}")
        except Exception as e:
            print(f"Error in _change_game_mode: {e}")

    def _change_rounds(self, index):
        """更改游戏轮数"""
        try:
            rounds_map = {0: 1, 1: 3, 2: 5}
            self.rounds_setting = rounds_map[index]
            self.result_label.setText(f"已切换到{self.rounds_combo.currentText()}")
        except Exception as e:
            print(f"Error in _change_rounds: {e}")

    def start_new_game(self):
        """开始新游戏"""
        self.is_playing = True
        self.round_paused = False
        self.round_confirmed = False
        self.current_gesture = None
        self.last_gesture_time = time.time()
        self.game_logic.game_state = GameState(best_of=self.rounds_setting)
        self.score_label.setText("比分: 0 - 0")
        self.result_label.setText("游戏开始！")
        self.player_gesture_label.setText("等待出手...")
        self.computer_gesture_label.setText("等待出手...")
        self.time_label.setText(f"剩余时间: {self.gesture_timeout:.1f}s")

        # 清空手势图片
        for frame in [self.player_frame, self.computer_frame]:
            image_label = frame.findChild(QLabel, "image_label")
            if image_label:
                image_label.clear()

    def closeEvent(self, event):
        """关闭窗口时释放摄像头"""
        self.camera.release()
        event.accept()

    def _load_gesture_images(self):
        """加载手势图片"""
        try:
            return {
                "rock": QPixmap("assets/rock.png"),
                "paper": QPixmap("assets/paper.png"),
                "scissors": QPixmap("assets/scissors.png"),
                "unknown": QPixmap()  # 空图片用于未知手势
            }
        except Exception as e:
            print(f"Error loading gesture images: {e}")
            return {}


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = GameWindow()
    window.show()
    sys.exit(app.exec())
