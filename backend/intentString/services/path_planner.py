from .astar import astar, smooth_path
from .map_loader import get_map

_map_instance = None


def _get_map():
    global _map_instance
    if _map_instance is None:
        _map_instance = get_map()
    return _map_instance


def plan_path(start_wx, start_wy, goal_wx, goal_wy, do_smooth=True):
    """
    실제 좌표(m) 기반 경로 계획.
    반환: {
        "path": [(wx, wy), ...],
        "length": float,
        "found": bool
    }
    """
    m    = _get_map()
    path = astar(m, (start_wx, start_wy), (goal_wx, goal_wy))

    if path is None:
        return {"found": False, "path": [], "length": 0.0}

    if do_smooth:
        path = smooth_path(path)

    length = sum(
        ((path[i+1][0] - path[i][0])**2 + (path[i+1][1] - path[i][1])**2) ** 0.5
        for i in range(len(path) - 1)
    )

    return {
        "found":  True,
        "path":   [{"x": wx, "y": wy} for wx, wy in path],
        "length": round(length, 3),
    }


def get_map_info():
    """맵 이미지 + 메타데이터 반환"""
    m = _get_map()
    return {
        "image": m.to_base64_png(),
        **m.meta(),
    }


def reload_map():
    """맵 파일 교체 후 재로드할 때 호출"""
    global _map_instance
    _map_instance = None
    _get_map()
