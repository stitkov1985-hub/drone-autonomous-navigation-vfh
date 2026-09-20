import cv2
import cv2.aruco as aruco
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import argparse

def detect_board_position(frame, board, camera_matrix, dist_coeffs, params, dict):
    """
    Определяет положение камеры относительно доски ArUco.

    Параметры:
    - frame: кадр из видеопотока.
    - board: объект ArUco доски.
    - camera_matrix: матрица камеры.
    - dist_coeffs: коэффициенты дисторсии камеры.
    """

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)


    corners, ids, rejectedImgPoints = aruco.detectMarkers(gray, dictionary=dict, parameters=params)

    if ids is not None:
        retval, board_rvec, board_tvec = aruco.estimatePoseBoard(corners, ids, board, camera_matrix,
                                                                 dist_coeffs, rvec=None, tvec=None)
        if retval:
            return board_rvec, board_tvec, corners, ids
    return None, None, corners, ids

def main(video_path):
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
    ax2.set_xlim([-0.25, 0.25])
    ax2.set_ylim([-0.25, 0.25])
    ax2.set_zlim([0, 0.35])
    iter = 0
    camera_matrix = np.array([[800, 0, 320], [0, 800, 320], [0, 0, 1]], dtype=np.float32)
    dist_coeffs = np.array([0, 0, 0, 0, 0], dtype=np.float32)

    parameters = aruco.DetectorParameters()
    # Создаем доску ArUco
    aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_250)
    # Заполняем параметры доски размер, размер маркера, расстояние между ними   
    board = aruco.GridBoard([4, 4], 0.02675, 0.00526, aruco_dict)
    
    cap = cv2.VideoCapture(video_path)
    if cap.isOpened():
        ret, frame = cap.read()
        frame = cv2.resize(frame, (640, 640))
        im = ax1.imshow(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    else:
        print("File open error!")
        exit(1)


    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.resize(frame, (640, 640))

        rvec, tvec, corners, ids = detect_board_position(frame, board, camera_matrix,
                                                         dist_coeffs, parameters, aruco_dict)

        if rvec is not None:
            frame = aruco.drawDetectedMarkers(frame, corners, ids)
            # Рисуем оси СК доски маркеров размером 0.5 м
            frame = cv2.drawFrameAxes(frame, camera_matrix, dist_coeffs, rvec, tvec, 0.5)
            # Переводим положение 
            R, _ = cv2.Rodrigues(rvec)
            R_inv = np.transpose(R)
            tvec_inv = np.dot(R_inv, tvec)
            x, y, z = tvec_inv
            # Выводим каждое пятое значение на график.
            if iter % 5 == 0:
                ax2.scatter(x, y, z, c='r', marker='o')
            iter += 1

        im.set_data(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        plt.pause(0.01)


    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Aruco board navigation example')
    parser.add_argument('--video_path', help='path to video file', default="../../aruco_board_example.mp4")
    args = parser.parse_args()
    main(args.video_path)
