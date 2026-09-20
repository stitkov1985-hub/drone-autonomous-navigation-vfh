#!/usr/bin/env python3
import os
import rosbag

# Принудительно отключаем графический интерфейс для работы в Docker
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

bag_path = '/app/swarm_flight.bag'
output_path = '/app/src/swarm_trajectory_graph.png'

if not os.path.exists(bag_path):
    print(f"Ошибка: Файл бага не найден по пути {bag_path}")
    exit(1)

print("Чтение данных из черного ящика...")
bag = rosbag.Bag(bag_path)

x_coords = []
y_coords = []

for topic, msg, t in bag.read_messages(topics=['/gazebo/model_states']):
    if 'iris' in msg.name:
        idx = msg.name.index('iris')
        pose = msg.pose[idx]
        x_coords.append(pose.position.x)
        y_coords.append(pose.position.y)

bag.close()

# БАЗА КООРДИНАТ НАШИХ ПРЕПЯТСТВИЙ (ИЗ ФАЙЛА МИРА)
trees = [
    (6.0, 3.5), (7.0, -4.0), (8.5, 1.5), (9.5, -2.0), (11.0, 5.0), (12.5, -5.5),
    (14.0, 0.0), (15.5, 3.2), (17.0, -3.8), (18.5, 6.0), (20.0, -1.5), (21.5, 2.5),
    (23.0, -5.0), (24.5, 4.5), (26.0, 0.5), (28.5, -3.0), (31.0, 2.0), (34.0, 0.0),
    (35.5, 5.5), (36.0, -4.5), (37.5, 1.0), (38.0, -2.5), (39.5, 3.5), (40.0, -6.0),
    (41.5, -0.5), (42.0, 4.0), (43.5, -3.5), (44.0, 2.0), (45.5, -1.5), (46.0, 5.0),
    (47.5, -5.0), (48.0, 0.5), (49.5, -3.0), (50.0, 3.0), (51.5, -6.5), (52.0, -0.5),
    (53.5, 4.5), (54.0, -4.0), (54.5, 1.5), (55.0, -2.0), (55.5, 6.0), (56.0, -5.5),
    (56.5, 0.0), (57.0, 3.0), (57.5, -3.5),
    # Боковые ряды расширения
    (10.0, 9.0), (15.0, 8.5), (20.0, 10.0), (25.0, 7.5), (30.0, 9.5), (35.0, 8.0), (40.0, 10.5), (45.0, 9.0), (50.0, 7.5), (55.0, 9.0),
    (8.0, -9.0), (13.0, -8.5), (19.0, -10.0), (24.0, -7.5), (29.0, -9.5), (34.0, -8.0), (39.0, -10.5), (44.0, -9.0), (49.0, -7.5), (54.0, -9.0)
]

boxes = [
    (2.0, 1.5), (15.0, -3.0), (38.0, 4.0) # Системные блоки
]
pallets = [
    (5.0, 0.0), (24.0, -1.0), (48.0, 3.5) # Поддоны
]

# СТРОИМ ГРАФИК
plt.figure(figsize=(12, 7))

# 1. Отрисовка деревьев
for i, tree in enumerate(trees):
    plt.plot(tree[0], tree[1], 'go', markersize=8, alpha=0.7, label='Дерево (Препятствие)' if i == 0 else "")

# 2. Отрисовка коробок и поддонов
for i, box in enumerate(boxes):
    plt.plot(box[0], box[1], 's', color='gray', markersize=6, label='Антропогенный мусор' if i == 0 else "")
for pallet in pallets:
    plt.plot(pallet[0], pallet[1], 's', color='brown', markersize=10)

# 3. Отрисовка траектории полета
plt.plot(x_coords, y_coords, label='Траектория БПЛА (Алгоритм VFH)', color='red', linewidth=2.5)

# Оформление
plt.axhline(0, color='black', linestyle='--', alpha=0.3)
plt.title('Результаты моделирования обхода препятствий БПЛА в лесном массиве', fontsize=12, fontweight='bold')
plt.xlabel('Координата X (Метры вперед к океану)', fontsize=10)
plt.ylabel('Координата Y (Метры уклонения вбок)', fontsize=10)
plt.grid(True, linestyle=':', alpha=0.6)
plt.legend(loc='upper left')

plt.xlim(-5, 65)
plt.ylim(-15, 15)

plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"Идеальный дипломный график сохранен в: {output_path}")
