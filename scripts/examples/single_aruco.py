import cv2
import cv2.aruco as aruco
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import argparse

def detect_marker_position(frame, marker_size, camera_matrix, dist_coeffs):
    """
    Определяет положение камеры относительно маркера.

    Параметры:
    - frame: кадр из видеопотока.
    - marker_size: размер маркера в метрах.
    - camera_matrix: матрица камеры.
    - dist_coeffs: коэффициенты дисторсии камеры.
    """

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_250)
    parameters = aruco.DetectorParameters_create()
    corners, ids, rejectedImgPoints = aruco.detectMarkers(gray, aruco_dict, parameters=parameters)

    if ids is not None:
        rvec, tvec, _ = aruco.estimatePoseSingleMarkers(corners, marker_size, camera_matrix, dist_coeffs)
        inv_tvec = -tvec
        return rvec, inv_tvec, corners, ids
    else:
        return None, None, corners, ids

def main(video_path):
    # Создание фигуры для отображения графика и текущего кадра
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))

    # Настройка осей
    ax1.set_xlabel('Pixels W')
    ax1.set_ylabel('Pixels H')
    ax2 = fig.add_subplot(1, 2, 2, projection='3d')
    ax2.set_title('3D Pose')
    ax2.set_xlabel('X (m)')
    ax2.set_ylabel('Y (m)')
    ax2.set_zlabel('Z (m)')
    ax1.set_title('Detected Marker')
    ax2.set_xlim([-0.25, 0.2])
    ax2.set_ylim([-0.25, 0.2])
    ax2.set_zlim([0, 0.6])

    # Значения матрицы камеры строго индивидуальны для каждой камеры
    camera_matrix = np.array([[640, 0, 320], [0, 640, 240], [0, 0, 1]], dtype=np.float32)
    dist_coeffs = np.array([0, 0, 0, 0, 0], dtype=np.float32)

    cap = cv2.VideoCapture(1)
    if cap.isOpened():
        ret, frame = cap.read()
        frame = cv2.resize(frame, (640, 640))
        im = ax1.imshow(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    else:
        exit(1)

    while cap.isOpened():
        ret, frame = cap.read()
        frame = cv2.resize(frame, (640, 640))
        if not ret:
            break

        rvecs, tvecs, corners, ids = detect_marker_position(frame, 0.03, camera_matrix, dist_coeffs)

        if rvecs is not None:
            frame = aruco.drawDetectedMarkers(frame, corners, ids)  # рисуем обнаруженные маркеры
            for idx, (rvec, tvec) in enumerate(zip(rvecs, tvecs)):
                frame = cv2.drawFrameAxes(frame, camera_matrix, dist_coeffs, rvec, tvec, 0.1)  # рисуем оси на маркере
                # Переводим вектор положения tvec в систему координат маркера из СК камеры
                R, _ = cv2.Rodrigues(rvec)
                R_inv = np.transpose(R)
                tvec_inv = np.dot(R_inv, tvec.transpose())
                # Добавляем 3D координаты на график
                x, y, z = tvec_inv
                ax2.scatter(x, y, z, c='r', marker='o')
        # Обновляем изображение на графике
        im.set_data(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        plt.pause(0.01) # Пауза для обновления графика

    # Закрываем видеофайл и освобождаем ресурсы
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    # Создаем парсер для обработки аргументов командной строки
    parser = argparse.ArgumentParser(description='Single aruco marker pose estimation example')
    parser.add_argument('--video_path', help='path to video file', default="../../single_marker_example.mp4")
    args = parser.parse_args() # Разбираем аргументы
    main(args.video_path) # Запускаем основную функцию с переданным путем к видеофайлу
