import cv2
from ultralytics import YOLO
import time
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# ============ 配置区域 ============
# 选择显示模式: 'oled', 'tft', 或 'pygame'
DISPLAY_MODE = "oled"  # 推荐使用pygame，兼容性最好

# 屏幕尺寸配置
SCREEN_WIDTH = 320
SCREEN_HEIGHT = 240

# OLED配置（如果使用OLED）
OLED_I2C_ADDRESS = 0x3C
OLED_WIDTH = 128
OLED_HEIGHT = 64

# ===================================


class DisplayManager:
    """显示管理器，支持多种小屏幕"""

    def __init__(self, mode="pygame"):
        self.mode = mode
        self.screen = None
        self.font = None

        if mode == "pygame":
            self._init_pygame()
        elif mode == "oled":
            self._init_oled()
        elif mode == "tft":
            self._init_tft()

    def _init_pygame(self):
        """初始化pygame显示（适用于HDMI小屏或测试）"""
        try:
            import pygame

            pygame.init()
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
            pygame.display.set_caption("YOLO Detection")
            self.font = pygame.font.Font(None, 24)
            self.small_font = pygame.font.Font(None, 18)
            print(f"Pygame显示初始化成功: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")
        except Exception as e:
            print(f"Pygame初始化失败: {e}")
            self.mode = None

    def _init_oled(self):
        """初始化OLED显示（I2C接口，如SSD1306）"""
        try:
            from luma.core.interface.serial import i2c
            from luma.core.render import canvas
            from luma.oled.device import ssd1306

            serial = i2c(port=1, address=OLED_I2C_ADDRESS)
            self.screen = ssd1306(serial, width=OLED_WIDTH, height=OLED_HEIGHT)
            print(f"OLED显示初始化成功: {OLED_WIDTH}x{OLED_HEIGHT}")
        except Exception as e:
            print(f"OLED初始化失败: {e}")
            print("请安装: pip install luma.oled")
            self.mode = None

    def _init_tft(self):
        """初始化TFT显示（SPI接口，如ST7789）"""
        try:
            from luma.core.interface.serial import spi
            from luma.lcd.device import st7789

            serial = spi(port=0, device=0, gpio_DC=24, gpio_RST=25)
            self.screen = st7789(serial, width=SCREEN_WIDTH, height=SCREEN_HEIGHT)
            print(f"TFT显示初始化成功: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")
        except Exception as e:
            print(f"TFT初始化失败: {e}")
            print("请安装: pip install luma.lcd")
            self.mode = None

    def display_detection_results(self, detected_objects, fps, frame_count):
        """显示检测结果"""
        if self.mode == "pygame":
            self._display_pygame(detected_objects, fps, frame_count)
        elif self.mode in ["oled", "tft"]:
            self._display_luma(detected_objects, fps, frame_count)

    def _display_pygame(self, detected_objects, fps, frame_count):
        """使用Pygame显示"""
        import pygame

        # 清空屏幕
        self.screen.fill((0, 0, 0))

        # 显示标题
        title = self.font.render("YOLO Detection", True, (0, 255, 0))
        self.screen.blit(title, (10, 10))

        # 显示FPS和帧数
        info = self.small_font.render(
            f"FPS: {fps:.1f} | Frame: {frame_count}", True, (255, 255, 0)
        )
        self.screen.blit(info, (10, 40))

        # 显示检测结果
        y_offset = 70
        if detected_objects:
            count_text = self.small_font.render(
                f"Detected: {len(detected_objects)} objects", True, (255, 255, 255)
            )
            self.screen.blit(count_text, (10, y_offset))
            y_offset += 25

            for i, obj in enumerate(detected_objects[:5]):  # 最多显示5个
                # 物体名称
                name_text = self.small_font.render(
                    f"{i+1}. {obj['name']}", True, (0, 255, 255)
                )
                self.screen.blit(name_text, (20, y_offset))
                y_offset += 20

                # 置信度
                conf_text = self.small_font.render(
                    f"   Conf: {obj['confidence']:.0%}", True, (200, 200, 200)
                )
                self.screen.blit(conf_text, (20, y_offset))
                y_offset += 25
        else:
            no_obj_text = self.small_font.render(
                "No objects detected", True, (128, 128, 128)
            )
            self.screen.blit(no_obj_text, (10, y_offset))

        # 更新显示
        pygame.display.flip()

        # 处理事件（避免窗口无响应）
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

        return True

    def _display_luma(self, detected_objects, fps, frame_count):
        """使用Luma显示（OLED/TFT）"""
        from luma.core.render import canvas

        with canvas(self.screen) as draw:
            # 显示标题
            draw.text((2, 0), "YOLO Detection", fill="white")
            draw.text((2, 12), f"FPS:{fps:.1f} F:{frame_count}", fill="white")

            # 显示检测结果
            y_offset = 26
            if detected_objects:
                draw.text(
                    (2, y_offset), f"Found: {len(detected_objects)}", fill="white"
                )
                y_offset += 12

                for i, obj in enumerate(detected_objects[:3]):  # OLED只显示3个
                    text = f"{i+1}.{obj['name']} {obj['confidence']:.0%}"
                    draw.text((2, y_offset), text, fill="white")
                    y_offset += 10
            else:
                draw.text((2, y_offset), "No objects", fill="white")

    def cleanup(self):
        """清理资源"""
        if self.mode == "pygame":
            import pygame

            pygame.quit()


def main():
    """
    在树莓派上使用YOLO进行实时物体检测，并显示在小屏幕上
    """
    # 初始化显示
    print("正在初始化显示...")
    display = DisplayManager(mode=DISPLAY_MODE)

    if display.mode is None:
        print("显示初始化失败，将只输出到控制台")

    # 加载YOLO模型
    print("正在加载YOLO模型...")
    model = YOLO("yolo11n.pt")
    print("模型加载完成!")

    # 打开摄像头
    print("正在打开摄像头...")
    cap = cv2.VideoCapture(0)

    # 设置摄像头分辨率
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        print("错误: 无法打开摄像头")
        return

    print("系统启动成功! 按 Ctrl+C 退出\n")

    frame_count = 0
    start_time = time.time()
    detection_interval = 5  # 每5帧检测一次
    last_detected_objects = []

    try:
        while True:
            # 读取摄像头画面
            ret, frame = cap.read()

            if not ret:
                print("错误: 无法读取摄像头画面")
                break

            frame_count += 1

            # 定期检测
            if frame_count % detection_interval == 0:
                results = model(frame, conf=0.5, verbose=False)

                # 处理检测结果
                detected_objects = []
                for result in results:
                    boxes = result.boxes

                    for box in boxes:
                        cls_id = int(box.cls[0])
                        class_name = model.names[cls_id]
                        confidence = float(box.conf[0])
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()

                        detected_objects.append(
                            {
                                "name": class_name,
                                "confidence": confidence,
                                "bbox": (int(x1), int(y1), int(x2), int(y2)),
                            }
                        )

                last_detected_objects = detected_objects

                # 控制台输出
                if detected_objects:
                    print(
                        f"\n[帧 {frame_count}] 检测到 {len(detected_objects)} 个物体:"
                    )
                    for i, obj in enumerate(detected_objects, 1):
                        print(f"  {i}. {obj['name']} ({obj['confidence']:.0%})")

            # 计算FPS
            elapsed_time = time.time() - start_time
            fps = frame_count / elapsed_time if elapsed_time > 0 else 0

            # 更新显示
            if display.mode:
                continue_running = display.display_detection_results(
                    last_detected_objects, fps, frame_count
                )
                if continue_running == False:
                    break

            # 控制帧率
            time.sleep(0.03)

    except KeyboardInterrupt:
        print("\n\n检测被用户中断")

    finally:
        # 释放资源
        cap.release()
        display.cleanup()

        # 显示统计信息
        total_time = time.time() - start_time
        avg_fps = frame_count / total_time if total_time > 0 else 0
        print(f"\n统计信息:")
        print(f"总帧数: {frame_count}")
        print(f"总时间: {total_time:.2f}秒")
        print(f"平均FPS: {avg_fps:.2f}")


if __name__ == "__main__":
    main()
