import cv2
import numpy as np
import argparse
import matplotlib.pyplot as plt


class BlockMatchingFlow:
    def __init__(self, img_width: int, img_height: int, subpixels_count: int = 16,
                 block_pixel_size: int = 50, border_margin: int = 50):
        """
        Конструктор класса BlockMatchingFlow.

        Args:
            img_width (int): Ширина изображения.
            img_height (int): Высота изображения.
            subpixels_count (int): Количество субпикселей для оптического потока.
            block_pixel_size (int): Размер блока для поиска смещений.
            border_margin (int): Отступ для расширения блока.
        """
        self.N = int(np.sqrt(subpixels_count))
        self.subpixels_count = self.N**2
        self.block_pixel_size = block_pixel_size
        self.border_margin = border_margin
        self.shifts = np.zeros((self.subpixels_count, 2))
        self.img_pose = np.zeros((self.subpixels_count, 2), dtype=np.int16)
        self.method = cv2.TM_CCOEFF_NORMED
        self.init_flow(img_width, img_height)

    def init_flow(self, w: int, h: int):
        """
        Инициализация сетки субпикселей.

        Args:
            w (int): Ширина изображения.
            h (int): Высота изображения.
        """
        w_step = (w // self.N) - (self.block_pixel_size + self.border_margin) // 2
        h_step = (h // self.N) - (self.block_pixel_size + self.border_margin) // 2
        # Рассчитываем заранее положение каждого субпикселя с учетом размера зоны
        # поиска и размеров изображения
        for idx, img_pose in enumerate(self.img_pose):
            img_pose[0] = (idx // self.N + 1) * w_step  # col
            img_pose[1] = (idx % self.N + 1) * h_step  # row

    def calculate_flow(self, cur_img: np.array, prev_img: np.array):
        """
        Расчет оптического потока.

        Args:
            cur_img: Текущее изображение.
            prev_img: Предыдущее изображение.

        Returns:
            shifts: Массив смещений.
        """
        # Для каждого субпикселя рассчитаем пиксельное смещение
        for idx, img_pose in enumerate(self.img_pose):
            # Получаем шаблон для поиска
            cur_sub_img = self.get_roi(cur_img, (img_pose[0], img_pose[1]), self.block_pixel_size)
            # Получаем зону поиска
            prev_sub_img = self.get_roi(prev_img, (img_pose[0], img_pose[1]),
                                        self.block_pixel_size + self.border_margin)
            #  Рассчитаем пиксельное смещение субпикселя
            self.shifts[idx] = self.calculate_subpixel_shift(cur_sub_img, prev_sub_img)

        # Посчитаем среднее пиксельное смещение.
        return self.shifts.mean(axis=0)

    def get_roi(self, img, pose, roi_size: int):
        """
        Получение области интереса (ROI) на изображении.

        Args:
            img: Исходное изображение.
            pose: Координаты центра ROI.
            roi_size: Размер ROI.

        Returns:
            roi: Область интереса (ROI).
        """
        # Определяем границы области интереса (ROI) с учетом отступа
        top = max(0, pose[1] - roi_size)
        bottom = min(img.shape[0], pose[1] + roi_size)
        left = max(0, pose[0] - roi_size)
        right = min(img.shape[1], pose[0] + roi_size)

        return img[top:bottom, left:right]

    def draw_blocks(self, image):
        """
        Отрисовка блоков с оптическим потоком на изображении.

        Args:
            image: Изображение.

        Returns:
            image: Изображение с нарисованными блоками.
        """
        for idx, (shift, img_pose) in enumerate(zip(self.shifts.reshape(-1, 2), self.img_pose.reshape(-1, 2))):
            # shift = (4, 0)
            # Вычисление радиуса вектора смещения
            radius = np.hypot(shift[0], shift[1])
            # Визуализация оптического потока на текущем кадре
            if radius > 3:
                top_left = np.array([img_pose[0] - self.block_pixel_size // 2,
                                     img_pose[1] - self.block_pixel_size // 2])
                bottom_right = np.array([img_pose[0] + self.block_pixel_size // 2,
                                         img_pose[1] + self.block_pixel_size // 2])

                cv2.rectangle(image, top_left, bottom_right, (255, 0, 0), 8)

                cv2.rectangle(image, top_left - self.border_margin,
                              bottom_right + self.border_margin, (0, 255, 255), 8)

                cv2.arrowedLine(image, (img_pose[0], img_pose[1]),
                                (int(img_pose[0] + shift[0]), int(img_pose[1] + shift[1])),
                                (0, 255, 0), 3, cv2.LINE_AA)
        return image

    def calculate_subpixel_shift(self, roi, img_for_matching):
        """
        Расчет субпиксельного смещения.

        Args:
            roi: Область интереса.
            img_for_matching: Изображение на котором осуществляется поиск(зона поиска).

        Returns:
            offset: Смещение.
        """
        w, h = roi.shape[0:2]
        center = (w // 2, h // 2)
        # Получим корреляционное изображение и найдем положение экстремума.
        res = cv2.matchTemplate(img_for_matching, roi, self.method)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

        # Рассчитаем пиксельный сдвиг между кадрами относительно зоны поиска
        offset = (max_loc[0] - center[0], max_loc[1] - center[1])
        if self.method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
            offset = (min_loc[0] - center[0], min_loc[1] - center[1])

        return offset


def main(video_source):
    # Инициализация списков для хранения интегрированных значений смещений
    x_integrated = [0]
    y_integrated = [0]

    # Инициализация видеопотока с заданным источником
    cap = cv2.VideoCapture(video_source)

    # Захватываем первый кадр для инициализации
    ret, prev_frame = cap.read()
    # Определение размеров кадра
    w, h = prev_frame.shape[0:2]

    # Создание экземпляра класса с алгоритмом оптического потока
    of = BlockMatchingFlow(w, h)

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
    # Инициализируем начальное изображение
    prev_frame_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)

    # Цикл обработки изображения
    while True:
        # Захватываем текущий кадр
        ret, current_frame = cap.read()
        if not ret:
            break

        # Преобразование текущего кадра в оттенки серого
        current_frame_gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)

        flow = of.calculate_flow(current_frame_gray, prev_frame_gray)

        # Обновление интегрированных значений смещений
        x_integrated.append(x_integrated[-1] + flow[0])
        y_integrated.append(y_integrated[-1] - flow[1])

        # Обновляем изображения на предыдущем кадре
        prev_frame_gray = current_frame_gray

        # Выполняем отрисовку фигур для визуализации
        current_frame = of.draw_blocks(current_frame)

        # Обновление графика и изображения
        line.set_xdata(x_integrated)
        line.set_ydata(y_integrated)
        axes[0].relim()
        axes[0].autoscale_view()
        im.set_data(cv2.cvtColor(current_frame, cv2.COLOR_BGR2RGB))
        plt.pause(0.01)

        # Прерывание цикла при нажатии клавиши 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

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
    # Запуск основной функции с переданным аргументом
    main(args.video_source)
