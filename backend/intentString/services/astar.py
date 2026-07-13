import heapq
import math


# 8방향 이동 (row_delta, col_delta, cost)
_NEIGHBORS = [
    (-1,  0, 1.0),   # 위
    ( 1,  0, 1.0),   # 아래
    ( 0, -1, 1.0),   # 왼쪽
    ( 0,  1, 1.0),   # 오른쪽
    (-1, -1, 1.414), # 좌상
    (-1,  1, 1.414), # 우상
    ( 1, -1, 1.414), # 좌하
    ( 1,  1, 1.414), # 우하
]


def _heuristic(a, b):
    """Euclidean 거리 휴리스틱"""
    return math.hypot(a[0] - b[0], a[1] - b[1])


def astar(map_loader, start_world, goal_world):
    """
    map_loader : MapLoader 인스턴스
    start_world: (wx, wy) 실제 좌표 [m]
    goal_world : (wx, wy) 실제 좌표 [m]

    반환: [(wx, wy), ...] 경로 리스트 또는 None
    """
    start = map_loader.world_to_grid(*start_world)
    goal  = map_loader.world_to_grid(*goal_world)

    if not map_loader.is_valid(*start):
        print(f"[A*] 시작점이 장애물 위: {start}")
        return None

    if not map_loader.is_valid(*goal):
        print(f"[A*] 목표점이 장애물 위: {goal}")
        return None

    # open_set: (f, g, node)
    open_set  = [(0.0, 0.0, start)]
    came_from = {}
    g_score   = {start: 0.0}

    while open_set:
        _, g, current = heapq.heappop(open_set)

        if current == goal:
            return _reconstruct(came_from, current, map_loader)

        # 이미 더 좋은 경로로 처리된 노드면 skip
        if g > g_score.get(current, float("inf")):
            continue

        for dr, dc, move_cost in _NEIGHBORS:
            nr, nc = current[0] + dr, current[1] + dc
            neighbor = (nr, nc)

            if not map_loader.is_valid(nr, nc):
                continue

            tentative_g = g_score[current] + move_cost

            if tentative_g < g_score.get(neighbor, float("inf")):
                came_from[neighbor] = current
                g_score[neighbor]   = tentative_g
                f = tentative_g + _heuristic(neighbor, goal)
                heapq.heappush(open_set, (f, tentative_g, neighbor))

    print("[A*] 경로를 찾을 수 없음")
    return None


def _reconstruct(came_from, current, map_loader):
    path = []
    while current in came_from:
        path.append(map_loader.grid_to_world(*current))
        current = came_from[current]
    path.append(map_loader.grid_to_world(*current))
    path.reverse()
    return path


def smooth_path(path, window=3):
    """
    이동 평균으로 경로를 부드럽게 만듦.
    Pure Pursuit에 넘기기 전에 적용하면 회전이 자연스러워짐.
    """
    if len(path) <= 2:
        return path

    smoothed = [path[0]]
    for i in range(1, len(path) - 1):
        xs = [path[j][0] for j in range(max(0, i - window), min(len(path), i + window + 1))]
        ys = [path[j][1] for j in range(max(0, i - window), min(len(path), i + window + 1))]
        smoothed.append((sum(xs) / len(xs), sum(ys) / len(ys)))
    smoothed.append(path[-1])
    return smoothed
