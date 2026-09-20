import cv2
import numpy as np
import matplotlib.pyplot as plt
import argparse


def main(video_source):
    # Инициализация видеопотока с заданным источником
    cap = cv2.VideoCapture(video_source)

    # Захватываем первый кадр для инициализации
    ret, prev_frame = cap.read()
    # Определение размеров кадра
    w, h = prev_frame.shape[0:2]
    # Определение центра кадра
    center = (w // 2, h // 2)
    # Инициализация списков для хранения интегрированных значений смещений
    x_integrated = [0]
    y_integrated = [0]

    # Создание фигуры для отображения графика и текущего кадра
    fig, axes = plt.subplots(1, 2, figsize=(10, 5))
    # Заголовки для графиков
    axes[0].set_title('Motion XY Graph')
    axes[1].set_title('Current Frame')
    # Отображение начального кадра
    im = axes[1].imshow(cv2.cvtColor(prev_frame, cv2.COLOR_BGR2RGB))
    # Инициализация линии на графике
    line, = axes[0].plot(x_integrated, y_integrated)
    # Включение сетки на графике
    axes[0].grid()

    # Преобразование кадра в формат с плавающей точкой
    prev_frame = prev_frame.astype('float32')
    # Преобразование кадра в оттенки серого
    prev_frame_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)

    while True:
        # Захватываем текущий кадр
        ret, current_frame = cap.read()
        if not ret:
            break

        # Преобразование текущего кадра в монохромное изображение
        current_frame_gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
        current_frame_gray = current_frame_gray.astype('float32')

        # Вычисление оптического потока между двумя кадрами
        flow, resp = cv2.phaseCorrelate(prev_frame_gray, current_frame_gray)

        # Получение смещений по осям X и Y
        dx = flow[0]
        dy = flow[1]

        # Вычисление радиуса вектора смещения
        radius = np.hypot(dx, dy)

        # Визуализация оптического потока на текущем кадре
        if radius > 3:
            cv2.circle(current_frame, center, int(round(radius)), (0, 255, 0), 3, cv2.LINE_AA)
            cv2.line(current_frame, center, (int(center[0] + dx), int(center[1] + dy)), (0, 255, 0), 3, cv2.LINE_AA)

        # Обновление интегрированных значений смещений
        x_integrated.append(x_integrated[-1] + dx)
        y_integrated.append(y_integrated[-1] + dy)
        prev_frame_gray = current_frame_gray

        # Обновление графика и изображения
        line.set_xdata(x_integrated)
        line.set_ydata(y_integrated)
        axes[0].relim()
        axes[0].autoscale_view()
        im.set_data(cv2.cvtColor(current_frame, cv2.COLOR_BGR2RGB))
        plt.pause(0.01)

    # Закрытие видеопотока и окон
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    # Создание парсера аргументов
    parser = argparse.ArgumentParser(description='Optical Flow Visualization')
    # Добавление аргумента для источника видео
    parser.add_argument('--video_source', default="../../test_of_example.mp4", help='Path to the video file.')
    # Разбор аргументов
    args = parser.parse_args()
    # Запуск основной функции с аргументом
    main(args.video_source)
