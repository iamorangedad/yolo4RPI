import cv2
from ultralytics import YOLO
import time
import os

# 设置环境变量，禁用GUI显示
os.environ["QT_QPA_PLATFORM"] = "offscreen"


def main():
    """
    在树莓派上使用YOLO进行实时物体检测（无GUI版本）
    """
    # 加载YOLOv8模型(使用nano版本以适应树莓派性能)
    print("正在加载YOLO模型...")
    model = YOLO("yolo11n.pt")  # yolov8n是最轻量级的模型
    print("模型加载完成!")

    # 打开摄像头
    print("正在打开摄像头...")
    cap = cv2.VideoCapture(0)

    # 设置摄像头分辨率(降低分辨率以提高性能)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        print("错误: 无法打开摄像头")
        return

    print("摄像头已打开,开始检测...")
    print("按 Ctrl+C 退出程序\n")

    frame_count = 0
    start_time = time.time()
    detection_interval = 10  # 每10帧检测一次，减少计算负担

    try:
        while True:
            # 读取摄像头画面
            ret, frame = cap.read()

            if not ret:
                print("错误: 无法读取摄像头画面")
                break

            frame_count += 1

            # 每隔几帧进行一次检测以提高性能
            if frame_count % detection_interval == 0:
                # 使用YOLO进行检测
                results = model(frame, conf=0.5, verbose=False)

                # 处理检测结果
                detected_objects = []
                for result in results:
                    boxes = result.boxes

                    for box in boxes:
                        # 获取类别名称
                        cls_id = int(box.cls[0])
                        class_name = model.names[cls_id]

                        # 获取置信度
                        confidence = float(box.conf[0])

                        # 获取边界框坐标
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()

                        detected_objects.append(
                            {
                                "name": class_name,
                                "confidence": confidence,
                                "bbox": (int(x1), int(y1), int(x2), int(y2)),
                            }
                        )

                # 输出检测结果
                if detected_objects:
                    print(f"\n{'='*50}")
                    print(f"帧 {frame_count} - 检测到 {len(detected_objects)} 个物体")
                    print(f"{'='*50}")

                    for i, obj in enumerate(detected_objects, 1):
                        print(f"\n物体 {i}:")
                        print(f"  名称: {obj['name']}")
                        print(f"  置信度: {obj['confidence']:.2%}")
                        print(
                            f"  位置: ({obj['bbox'][0]}, {obj['bbox'][1]}) -> ({obj['bbox'][2]}, {obj['bbox'][3]})"
                        )
                else:
                    print(f"\n帧 {frame_count} - 未检测到物体")

            # 每30帧显示一次FPS
            if frame_count % 30 == 0:
                elapsed_time = time.time() - start_time
                fps = frame_count / elapsed_time
                print(f"\n[性能] 当前FPS: {fps:.2f}")

            # 短暂延迟，避免CPU占用过高
            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n\n检测被用户中断")

    finally:
        # 释放资源
        cap.release()
        # 不再调用destroyAllWindows，避免Qt错误

        # 显示统计信息
        total_time = time.time() - start_time
        avg_fps = frame_count / total_time if total_time > 0 else 0
        print(f"\n统计信息:")
        print(f"总帧数: {frame_count}")
        print(f"总时间: {total_time:.2f}秒")
        print(f"平均FPS: {avg_fps:.2f}")


if __name__ == "__main__":
    main()
