import cv2
import cv2.aruco as aruco
import argparse

def generate_aruco_board(output_filename='aruco_board.png', markersX=5,
                         markersY=7, markerLength=1, markerSeparation:float=0.2,
                         pixel_per_meter: int = 200, margin_size:int =100,
                         border_bit:int = 1):
    """
    Генерирует ArUco доску и сохраняет ее в файл.

    Параметры:
    - output_filename: имя файла для сохранения доски.
    - markersX: количество маркеров по горизонтали.
    - markersY: количество маркеров по вертикали.
    - markerLength: размер каждого маркера в метрах.
    - markerSeparation: расстояние между маркерами в метрах.
    - pixel_per_meter: количество пикселей на метр.
    - margin_size: размер отступа в пикселях.
    - border_bit: ширина границы маркера в битах.
    """

    # Выберите предопределенный словарь ArUco
    aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_250)

    # Создайте доску
    board = aruco.GridBoard([markersX, markersY], markerLength, markerSeparation, aruco_dict)

    board_width = (markersX * markerLength + (markersX - 1) * markerSeparation) * pixel_per_meter
    board_height = (markersY * markerLength + (markersY - 1) * markerSeparation) * pixel_per_meter
    size = (int(board_width), int(board_height))

    # Получите изображение доски
    board_image = cv2.aruco.drawPlanarBoard(board, size, margin_size, border_bit)

    # Сохраните изображение
    cv2.imwrite(output_filename, board_image)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Генерация ArUco доски и сохранение ее в файл.")
    parser.add_argument("--output_filename", default="aruco_board.png", help="Имя файла для сохранения доски.")
    parser.add_argument("--markersX", type=int, default=5, help="Количество маркеров по горизонтали.")
    parser.add_argument("--markersY", type=int, default=7, help="Количество маркеров по вертикали.")
    parser.add_argument("--markerLength", type=float, default=1, help="Размер каждого маркера в метрах.")
    parser.add_argument("--markerSeparation", type=float, default=0.2, help="Расстояние между маркерами в метрах.")
    parser.add_argument("--pixel_per_meter", type=int, default=200, help="Количество пикселей на метр.")
    parser.add_argument("--margin_size", type=int, default=100, help="Размер отступа в пикселях.")
    parser.add_argument("--border_bit", type=int, default=1, help="Ширина границы маркера в битах.")

    args = parser.parse_args()

    generate_aruco_board(args.output_filename, args.markersX, args.markersY, args.markerLength,
                         args.markerSeparation, args.pixel_per_meter, args.margin_size, args.border_bit)
