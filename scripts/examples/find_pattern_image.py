import cv2
import numpy as np
from matplotlib import pyplot as plt

# Загрузка исходного изображения
img = cv2.imread('../../.img/tennis.jpg')
assert img is not None, "File could not be read, check with os.path.exists()"
img2 = img.copy()

# Загрузка шаблона
template = cv2.imread('../../.img/ball.jpg')
assert template is not None, "File could not be read, check with os.path.exists()"

# Получение размеров шаблона
w, h = template.shape[0:2]

# Список методов для сравнения
methods = ['cv2.TM_CCOEFF', 'cv2.TM_CCOEFF_NORMED', 'cv2.TM_CCORR',
           'cv2.TM_CCORR_NORMED', 'cv2.TM_SQDIFF', 'cv2.TM_SQDIFF_NORMED']

# Создание фигуры для вывода всех изображений на одном графике
plt.figure(figsize=(20, 18))

for idx, meth in enumerate(methods, 1):
    img = img2.copy()
    method = eval(meth)

    # Применение метода сопоставления шаблона
    res = cv2.matchTemplate(img, template, method)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

    # Выбор координат для рисования прямоугольника
    if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
        top_left = min_loc
    else:
        top_left = max_loc
    bottom_right = (top_left[0] + w, top_left[1] + h)

    # Рисование красного прямоугольника вокруг найденного объекта
    cv2.rectangle(img, top_left, bottom_right, (0, 0, 255), 8)

    # Вывод результатов
    plt.subplot(3, 4, idx*2-1), plt.imshow(res, cmap='viridis')
    plt.title(meth.split('.')[-1]), plt.xticks([]), plt.yticks([])
    plt.subplot(3, 4, idx*2), plt.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    plt.title('Detected Object'), plt.xticks([]), plt.yticks([])

plt.tight_layout()
plt.show()
