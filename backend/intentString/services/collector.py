import json
import time
import statistics


LIMO_HOST = "192.168.50.190"
LIMO_PORT = 9090


# ── ODS Reduction ───────────────────────────────────────────
def reduce_odom(samples: list[dict]) -> dict:
    """raw odom 샘플 목록 → 통계 요약 (ODS Reduction)"""
    if not samples:
        return {}

    vx_list = [s["vx"] for s in samples]
    vz_list = [s["vz"] for s in samples]

    return {
        "samples": len(samples),
        "vx_mean": round(statistics.mean(vx_list), 4),
        "vx_max":  round(max(vx_list), 4),
        "vz_mean": round(statistics.mean(vz_list), 4),
        "last_x":  round(samples[-1]["x"], 4),
        "last_y":  round(samples[-1]["y"], 4),
    }


def reduce_scan(samples: list[dict]) -> dict:
    """raw scan 샘플 목록 → 통계 요약 (ODS Reduction)"""
    if not samples:
        return {}

    min_dists = [s["min_dist"] for s in samples]
    return {
        "samples":       len(samples),
        "min_dist_mean": round(statistics.mean(min_dists), 3),
        "min_dist_min":  round(min(min_dists), 3),
        "obstacle_detected": min(min_dists) < 0.3,
    }


# ── ODS Transformation ──────────────────────────────────────
def transform_to_text(odom: dict, scan: dict) -> str:
    """수치 요약 → LLM이 이해할 자연어 (ODS Transformation)"""
    lines = []

    if odom:
        moving = abs(odom.get("vx_mean", 0)) > 0.01 or abs(odom.get("vz_mean", 0)) > 0.01
        lines.append(
            f"LIMO 상태: {'이동 중' if moving else '정지'} | "
            f"평균 선속도 {odom['vx_mean']} m/s | "
            f"평균 각속도 {odom['vz_mean']} rad/s | "
            f"현재 위치 ({odom['last_x']}, {odom['last_y']})"
        )

    if scan:
        obs = scan.get("obstacle_detected", False)
        lines.append(
            f"장애물: {'감지됨 (최소 {:.2f}m)'.format(scan['min_dist_min']) if obs else '없음'} | "
            f"전방 최소 거리 {scan['min_dist_mean']} m"
        )

    return " / ".join(lines) if lines else "데이터 없음"


# ── WebSocket 수집 ──────────────────────────────────────────
def _collect_topic(topic: str, msg_type: str, duration: float = 2.0) -> list[dict]:
    """rosbridge WebSocket으로 단일 토픽 구독 및 메시지 수집"""
    try:
        import websocket

        ws = websocket.create_connection(f"ws://{LIMO_HOST}:{LIMO_PORT}", timeout=5)
        ws.send(json.dumps({
            "op": "subscribe",
            "topic": topic,
            "type": msg_type,
        }))

        raw_samples = []
        end_time = time.time() + duration
        ws.settimeout(0.5)

        while time.time() < end_time:
            try:
                msg = json.loads(ws.recv())
                if msg.get("op") == "publish":
                    raw_samples.append(msg.get("msg", {}))
            except Exception:
                pass

        ws.close()
        return raw_samples

    except Exception as e:
        print(f"[Collector] {topic} 수집 실패: {e}")
        return []


# ── 파싱 ────────────────────────────────────────────────────
def _parse_odom(raw: list[dict]) -> list[dict]:
    parsed = []
    for msg in raw:
        try:
            pos = msg["pose"]["pose"]["position"]
            vel = msg["twist"]["twist"]["linear"]
            ang = msg["twist"]["twist"]["angular"]
            parsed.append({
                "x":  pos["x"],
                "y":  pos["y"],
                "vx": vel["x"],
                "vz": ang["z"],
            })
        except (KeyError, TypeError):
            pass
    return parsed


def _parse_scan(raw: list[dict]) -> list[dict]:
    parsed = []
    for msg in raw:
        try:
            ranges = [r for r in msg["ranges"] if 0.01 < r < 10.0]
            if ranges:
                parsed.append({"min_dist": min(ranges)})
        except (KeyError, TypeError):
            pass
    return parsed


# ── Public API ───────────────────────────────────────────────
def collect_limo_status(duration: float = 2.0) -> dict:
    """
    LIMO 실행 후 상태 수집 (Confucius Collector 패턴)
    - /odom : 위치 & 속도
    - /scan : 장애물 거리
    Returns: {odom, scan, summary, text}
    """
    print(f"[Collector] {duration}s 동안 LIMO 상태 수집 시작")

    raw_odom = _collect_topic("/odom", "nav_msgs/msg/Odometry", duration)
    raw_scan = _collect_topic("/scan", "sensor_msgs/msg/LaserScan", duration)

    odom_samples = _parse_odom(raw_odom)
    scan_samples  = _parse_scan(raw_scan)

    odom_reduced = reduce_odom(odom_samples)
    scan_reduced  = reduce_scan(scan_samples)
    text          = transform_to_text(odom_reduced, scan_reduced)

    print(f"[Collector] 수집 완료 → {text}")

    return {
        "odom":    odom_reduced,
        "scan":    scan_reduced,
        "summary": text,
        "status":  "ok" if (odom_samples or scan_samples) else "unreachable",
    }
