import cv2
import tkinter as tk
from tkinter import Button
from PIL import Image, ImageTk
import argparse


class ObjectTracker:
    def __init__(self, roi_margin: int = 50, method=cv2.TM_CCORR_NORMED):
        """
        Конструктор класса ObjectTracker.

        Args:
            roi_margin (int): Предельное значение отступа ROI.
            method: Метод сравнения шаблона.
        """
        # Инициализация объекта трекинга
        self.method = method
        # Устанавливаем предельное значение отступа ROI
        self.roi_margin = roi_margin
        self.top_left = None
        self.bottom_right = None
        self.roi = None

    def get_image_for_matching(self, img, pose_x, pose_y):
        """
         Получение изображения для сравнения с шаблоном.

         Args:
             img: Исходное изображение.
             pose_x: Координата X.
             pose_y: Координата Y.
        """
        # Определяем границы области интереса (ROI) с учетом отступа
        top = max(0, self.top_left[1] - self.roi_margin)
        bottom = min(img.shape[0], self.bottom_right[1] + self.roi_margin)
        left = max(0, self.top_left[0] - self.roi_margin)
        right = min(img.shape[1], self.bottom_right[0] + self.roi_margin)

        # Извлекаем область для сравнения с шаблоном
        img_for_matching = img[top:bottom, left:right]

    def track(self, img):
        """
        Осуществление слежения за объектом на изображении.

        Args:
            img: Изображение для трекинга.
        """
        img_copy = img.copy()

        # Определяем границы области интереса (ROI) с учетом отступа
        top = max(0, self.top_left[1] - self.roi_margin)
        bottom = min(img.shape[0], self.bottom_right[1] + self.roi_margin)
        left = max(0, self.top_left[0] - self.roi_margin)
        right = min(img.shape[1], self.bottom_right[0] + self.roi_margin)

        # Извлекаем область для сравнения с шаблоном
        img_for_matching = img[top:bottom, left:right]

        # Убеждаемся, что размеры шаблона не превышают размеры img_for_matching
        self.roi = self.roi[
                   : min(self.roi.shape[0], img_for_matching.shape[0]),
                   : min(self.roi.shape[1], img_for_matching.shape[1]),
                   ]

        # Производим сравнение шаблона с img_for_matching
        res = cv2.matchTemplate(self.roi, img_for_matching, self.method)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

        offset = self.roi_margin
        if self.method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
            offset *= -1

        # Обновляем координаты top_left и bottom_right с учетом смещения
        self.top_left = (
            max_loc[0] + self.top_left[0] - offset,
            max_loc[1] + self.top_left[1] - offset,
        )
        self.bottom_right = (
            self.top_left[0] + self.roi.shape[1],
            self.top_left[1] + self.roi.shape[0],
        )

        # Обновляем ROI на основе обработанного изображения
        self.roi = img_copy[
                   self.top_left[1]: self.bottom_right[1], self.top_left[0]: self.bottom_right[0]
                   ]

    def draw_rectangles(self, img):
        """
        Отрисовка прямоугольников на изображении.
        Внутренний - зона за которой осуществляется слежения.
        Внешний - зона в которой осуществляется поиск зоны слежения,
         относительно предыдущего кадра.
        Args:
            img: Изображение для отрисовки.
        """
        # Цвета для прямоугольников
        rectangle_color = (0, 0, 255)
        roi_rectangle_color = (0, 255, 0)

        # Рисуем прямоугольник для трекинга объекта
        cv2.rectangle(img, self.top_left, self.bottom_right, rectangle_color, 8)

        # Рисуем прямоугольник вокруг области интереса (ROI)
        cv2.rectangle(
            img,
            (self.top_left[0] - self.roi_margin, self.top_left[1] - self.roi_margin),
            (self.bottom_right[0] + self.roi_margin, self.bottom_right[1] + self.roi_margin),
            roi_rectangle_color,
            8,
        )
        return img

    def set_roi(self, roi, top_left, bottom_right):
        # Устанавливаем шаблон (ROI) и его координаты
        self.top_left = top_left
        self.bottom_right = bottom_right
        self.roi = roi


class ImageROISelector:
    def __init__(self, img):
        # Инициализация класса выбора области интереса
        self.image = img
        self.temp_image = self.image.copy()  # Создание копии изображения для временной обработки
        self.roi_points = []  # Список точек, определяющих границы области интереса (ROI)
        self.roi_selected = False  # Флаг, указывающий, была ли выбрана область интереса

    def select_roi(self, event, x, y, flags, param):
        # Метод обработки событий мыши для выбора ROI
        if event == cv2.EVENT_LBUTTONDOWN:
            self.roi_points = [(x, y)]  # Запоминаем начальную точку выбора
        elif event == cv2.EVENT_LBUTTONUP:
            self.roi_points.append((x, y))  # Запоминаем конечную точку выбора
            cv2.rectangle(self.temp_image, self.roi_points[0], self.roi_points[1], (0, 0, 255), 2)
            cv2.imshow("window", self.temp_image)  # Отображаем обновленное изображение с прямоугольником
            self.roi_selected = True  # Устанавливаем флаг, что ROI была выбрана

    def show_image(self):
        # Метод для отображения изображения с возможностью выбора ROI
        cv2.namedWindow("window")  # Создаем окно для выбора ROI
        cv2.setMouseCallback("window", self.select_roi)  # Устанавливаем обработчик событий мыши
        while True:
            cv2.imshow("window", self.temp_image)  # Отображаем текущее состояние изображения
            key = cv2.waitKey(1) & 0xFF
            if key == 27 or self.roi_selected:  # Нажатие 'ESC' или выбор ROI завершает цикл
                break

        self.show_tkinter_window()  # После выбора ROI, отображаем окно с кнопками в Tkinter

    def show_tkinter_window(self):
        # Метод для отображения окна Tkinter с изображением и кнопками
        self.root = tk.Tk()
        self.root.title("ROI Selector")

        cv2image = cv2.cvtColor(self.temp_image, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(cv2image)
        imgtk = ImageTk.PhotoImage(image=img)

        panel = tk.Label(self.root, image=imgtk)
        panel.pack(padx=10, pady=10)

        continue_button = Button(self.root, text="Continue", command=self.on_continue)
        continue_button.pack(side=tk.LEFT, padx=10, pady=10)

        retry_button = Button(self.root, text="Retry", command=self.on_retry)
        retry_button.pack(side=tk.LEFT, padx=10, pady=10)

        self.root.mainloop()

    def on_continue(self):
        # Обработчик нажатия кнопки "Continue"
        print("Continue pressed")
        self.root.destroy()  # Закрываем окно Tkinter

    def on_retry(self):
        # Обработчик нажатия кнопки "Retry"
        print("Retry pressed")
        self.root.destroy()  # Закрываем окно Tkinter
        self.temp_image = self.image.copy()  # Восстанавливаем временное изображение
        self.roi_points = []  # Сбрасываем точки ROI
        self.roi_selected = False  # Сбрасываем флаг выбора ROI
        self.show_image()  # Отображаем изображение снова для выбора ROI

    def get_roi(self):
        # Метод для получения выбранной ROI и ее координат
        if len(self.roi_points) == 2:
            pt1, pt2 = self.roi_points
            roi = self.image[pt1[1]: pt2[1], pt1[0]: pt2[0]]  # Извлекаем ROI из исходного изображения
            return roi, pt1, pt2
        return None  # Возвращаем None, если ROI не выбран


def main(video_source):
    # Инициализация захвата видеопотока с камеры
    cap = cv2.VideoCapture(video_source)
    ret, frame = cap.read()

    # Создание объекта для выбора области интереса
    selector = ImageROISelector(frame)
    selector.show_image()
    roi, top_left, bottom_right = selector.get_roi()

    # Создание объекта трекинга и установка шаблона (ROI)
    tracker = ObjectTracker()
    tracker.set_roi(roi, top_left, bottom_right)

    # Цикл обработки видео и трекинга объекта
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        # Вызываем метод отслеживающий перемещение искомой области
        tracker.track(frame)
        # Выполняем отрисовку прямоуголтника внутри искомой области
        frame = tracker.draw_rectangles(frame)

        # Вывод обработанного изображения с прямоугольниками
        cv2.imshow('window', frame)

        # Прерывание цикла при нажатии клавиши 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Освобождение ресурсов и закрытие окон
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    # Создание парсера аргументов
    parser = argparse.ArgumentParser(description='Optical Flow Visualization')
    # Добавление аргумента для источника видео
    parser.add_argument('--video_source', default="../../tracking_test.mp4", help='Path to the video file.')
    # Разбор аргументов
    args = parser.parse_args()
    # Запуск основной функции с переданным аргументом
    main(args.video_source)
