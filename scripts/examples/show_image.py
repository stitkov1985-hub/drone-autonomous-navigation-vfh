# Импортируем необходимые библиотеки
import cv2

# Инициализируем камеру. 0 означает, что мы используем стандартную камеру устройства.
# Вместо 0 можно указать путь к любому файлу например /dev/v4l/by-id/... или /home/user/my_video.mp4
# Если 0 не подойдет, попробуйте другие источники(1, 2, ...) или снимите видео если у вас нет камеры
cap = cv2.VideoCapture(0)

# Проверяем, инициализирована ли камера успешно
if not cap.isOpened():
    print("Error: camera not found.")
    exit()

while cap.isOpened():
    # Читаем кадр из видеопотока
    ret, frame = cap.read()

    # Проверяем, прочитан ли кадр успешно
    if not ret:
        print("Error: video frame read error.")
        break

    # Добавляем текст на картинку
    cv2.putText(frame, 'Hello, uav programming!', (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)

    # Отображаем картинку
    cv2.imshow('camera', frame)

    # Если пользователь нажмет клавишу 'q', выходим из цикла
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Освобождаем ресурсы и закрываем все окна
cap.release()
cv2.destroyAllWindows()