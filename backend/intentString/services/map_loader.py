import numpy as np
import yaml
import base64
import io
from PIL import Image


class MapLoader:
    def __init__(self, pgm_path=None, yaml_path=None):
        if pgm_path and yaml_path:
            self._load_from_file(pgm_path, yaml_path)
        else:
            self._load_test_map()

    def _load_from_file(self, pgm_path, yaml_path):
        with open(yaml_path, "r") as f:
            meta = yaml.safe_load(f)

        self.resolution = float(meta["resolution"])
        self.origin = meta["origin"][:2]          # [x, y]
        free_thresh = meta.get("free_thresh", 0.196)
        occ_thresh  = meta.get("occupied_thresh", 0.65)
        negate      = meta.get("negate", 0)

        img = Image.open(pgm_path).convert("L")
        arr = np.array(img, dtype=np.float32) / 255.0

        if negate:
            arr = 1.0 - arr

        # 0 = 이동 가능, 1 = 장애물/미탐색
        self.grid = np.ones(arr.shape, dtype=np.uint8)
        self.grid[arr >= (1.0 - free_thresh)] = 0   # 밝은 픽셀 = free
        self.grid[arr <= (1.0 - occ_thresh)]  = 1   # 어두운 픽셀 = obstacle

        self.height, self.width = self.grid.shape
        self._raw_image = img

    def _load_test_map(self):
        """실제 맵 없을 때 사용하는 테스트 맵 (SDV_Robocar 환경 모사)"""
        self.resolution = 0.5          # 셀 하나 = 0.5m
        self.origin     = [0.0, -10.0] # 맵 좌하단 실제 좌표

        W, H = 62, 42   # 31m x 21m
        grid = np.zeros((H, W), dtype=np.uint8)

        # 외벽
        grid[0, :]  = 1
        grid[-1, :] = 1
        grid[:, 0]  = 1
        grid[:, -1] = 1

        # 장애물 A (중앙 왼쪽)
        grid[15:25, 20:24] = 1

        # 장애물 B (중앙 오른쪽)
        grid[15:25, 38:42] = 1

        self.grid = grid
        self.height, self.width = grid.shape

        # 테스트용 이미지 생성 (흰=free, 검=obstacle)
        vis = np.where(grid == 0, 255, 0).astype(np.uint8)
        self._raw_image = Image.fromarray(vis, mode="L")

    # ── 좌표 변환 ─────────────────────────────────────────

    def world_to_grid(self, wx, wy):
        """실제 좌표(m) → 그리드 (row, col)"""
        col = int((wx - self.origin[0]) / self.resolution)
        row = int(self.height - (wy - self.origin[1]) / self.resolution)
        return row, col

    def grid_to_world(self, row, col):
        """그리드 (row, col) → 실제 좌표(m)"""
        wx = self.origin[0] + col * self.resolution
        wy = self.origin[1] + (self.height - row) * self.resolution
        return wx, wy

    def is_valid(self, row, col):
        if row < 0 or row >= self.height or col < 0 or col >= self.width:
            return False
        return self.grid[row][col] == 0

    # ── 이미지 직렬화 ──────────────────────────────────────

    def to_base64_png(self):
        """맵을 base64 PNG로 변환 (프론트엔드 전송용)"""
        # 흰=free, 검=obstacle, 회=unknown 시각화
        vis = np.full(self.grid.shape, 128, dtype=np.uint8)
        vis[self.grid == 0] = 255
        vis[self.grid == 1] = 0

        img = Image.fromarray(vis, mode="L").convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()

    def meta(self):
        return {
            "resolution": self.resolution,
            "origin":     self.origin,
            "width":      self.width,
            "height":     self.height,
        }


# 싱글턴 — 앱 시작 시 한 번만 로드
import os

_MAP_DIR  = os.path.join(os.path.dirname(__file__), "..", "..", "map")
_PGM_PATH = os.path.join(_MAP_DIR, "robot_map.pgm")
_YAML_PATH = os.path.join(_MAP_DIR, "robot_map.yaml")

def get_map() -> MapLoader:
    if os.path.exists(_PGM_PATH) and os.path.exists(_YAML_PATH):
        return MapLoader(_PGM_PATH, _YAML_PATH)
    return MapLoader()   # 테스트 맵
