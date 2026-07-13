import React, { useEffect, useRef, useState, useCallback } from "react";

const API_MAP      = "http://localhost:8000/api/map/";
const API_PATHPLAN = "http://localhost:8000/api/pathplan/";
const API_PATHEXEC = "http://localhost:8000/api/pathexec/";
const HEADERS      = { "Content-Type": "application/json" };
const CANVAS_W     = 900;
const CANVAS_H     = 650;
const ROSBRIDGE_WS = "ws://192.168.50.165:9090";

export default function MapModal({ onClose }) {
  const canvasRef = useRef(null);
  const wsRef     = useRef(null);

  const [mapData,   setMapData]   = useState(null);
  const [mapImg,    setMapImg]    = useState(null);
  const [path,      setPath]      = useState([]);
  const [goal,      setGoal]      = useState(null);
  const [robotPos,  setRobotPos]  = useState(null);   // null = 위치 미수신
  const [loading,   setLoading]   = useState(false);
  const [moving,    setMoving]    = useState(false);
  const [status,    setStatus]    = useState("맵 로딩 중...");
  const [rosStatus, setRosStatus] = useState("ROS 연결 중...");

  // ── 맵 로드 ─────────────────────────────────────────
  useEffect(() => {
    fetch(API_MAP)
      .then(r => r.json())
      .then(data => {
        setMapData(data);
        const img = new Image();
        img.src = `data:image/png;base64,${data.image}`;
        img.onload = () => { setMapImg(img); setStatus("맵 클릭으로 목표 지정"); };
      })
      .catch(() => setStatus("맵 로드 실패 — 백엔드 확인"));
  }, []);

  // ── rosbridge WebSocket — 로봇 실시간 위치 ──────────
  useEffect(() => {
    const ws = new WebSocket(ROSBRIDGE_WS);
    wsRef.current = ws;

    ws.onopen = () => {
      setRosStatus("ROS 연결됨");
      ws.send(JSON.stringify({
        op: "subscribe",
        topic: "/odom",
        type: "nav_msgs/msg/Odometry",
        throttle_rate: 200,
      }));
    };

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        if (msg.op === "publish" && msg.topic === "/odom") {
          const pos = msg.msg.pose.pose.position;
          setRobotPos({ x: pos.x, y: pos.y });
        }
      } catch (_) {}
    };

    ws.onerror = () => setRosStatus("ROS 연결 실패 — 우클릭으로 위치 수동 설정");
    ws.onclose = () => setRosStatus("ROS 연결 끊김");

    return () => ws.close();
  }, []);

  // ── Canvas 렌더링 ────────────────────────────────────
  const draw = useCallback(() => {
    if (!canvasRef.current || !mapImg || !mapData) return;
    const canvas = canvasRef.current;
    const ctx    = canvas.getContext("2d");

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(mapImg, 0, 0, canvas.width, canvas.height);

    const scaleX = canvas.width  / mapData.width;
    const scaleY = canvas.height / mapData.height;

    // A* 경로 (파란 선)
    if (path.length > 1) {
      ctx.strokeStyle = "#2196F3";
      ctx.lineWidth   = 2;
      ctx.beginPath();
      path.forEach((pt, i) => {
        const [px, py] = worldToCanvas(pt.x, pt.y, mapData, scaleX, scaleY);
        i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
      });
      ctx.stroke();
    }

    // 목표점 (빨간 X)
    if (goal) {
      const [px, py] = worldToCanvas(goal.x, goal.y, mapData, scaleX, scaleY);
      ctx.strokeStyle = "#f44336";
      ctx.lineWidth   = 3;
      ctx.beginPath();
      ctx.moveTo(px - 8, py - 8); ctx.lineTo(px + 8, py + 8);
      ctx.moveTo(px + 8, py - 8); ctx.lineTo(px - 8, py + 8);
      ctx.stroke();
    }

    // 로봇 위치 (초록 원)
    if (robotPos) {
      const [px, py] = worldToCanvas(robotPos.x, robotPos.y, mapData, scaleX, scaleY);
      ctx.fillStyle   = "#4CAF50";
      ctx.strokeStyle = "#fff";
      ctx.lineWidth   = 2;
      ctx.beginPath();
      ctx.arc(px, py, 7, 0, 2 * Math.PI);
      ctx.fill();
      ctx.stroke();
    }
  }, [mapImg, mapData, path, goal, robotPos]);

  useEffect(() => { draw(); }, [draw]);

  // ── 우클릭 → 로봇 시작 위치 수동 설정 ──────────────
  const handleCanvasRightClick = useCallback((e) => {
    e.preventDefault();
    if (!mapData || !canvasRef.current) return;
    const rect   = canvasRef.current.getBoundingClientRect();
    const scaleX = canvasRef.current.width  / rect.width;
    const scaleY = canvasRef.current.height / rect.height;
    const cx = (e.clientX - rect.left) * scaleX;
    const cy = (e.clientY - rect.top)  * scaleY;
    const [wx, wy] = canvasToWorld(cx, cy, mapData);
    setRobotPos({ x: wx, y: wy });
    setStatus(`로봇 위치 수동 설정: (${wx.toFixed(2)}, ${wy.toFixed(2)})`);
  }, [mapData]);

  // ── 좌클릭 → 목표 설정 + A* 요청 ────────────────────
  const handleCanvasClick = useCallback(async (e) => {
    if (!mapData || !canvasRef.current || !robotPos) {
      setStatus("로봇 위치 미확인 — 우클릭으로 시작점 설정");
      return;
    }

    const rect   = canvasRef.current.getBoundingClientRect();
    const scaleX = canvasRef.current.width  / rect.width;
    const scaleY = canvasRef.current.height / rect.height;

    const cx = (e.clientX - rect.left)  * scaleX;
    const cy = (e.clientY - rect.top)   * scaleY;

    const [wx, wy] = canvasToWorld(cx, cy, mapData);
    setGoal({ x: wx, y: wy });
    setStatus(`목표: (${wx.toFixed(2)}, ${wy.toFixed(2)}) — 경로 탐색 중...`);
    setPath([]);
    setLoading(true);

    try {
      const res = await fetch(API_PATHPLAN, {
        method:  "POST",
        headers: HEADERS,
        body:    JSON.stringify({
          start_x: robotPos.x,
          start_y: robotPos.y,
          goal_x:  wx,
          goal_y:  wy,
        }),
      });
      const data = await res.json();

      if (data.found) {
        setPath(data.path);
        setStatus(`경로 찾음 — ${data.length.toFixed(1)}m / ${data.path.length}포인트`);
      } else {
        setStatus("경로를 찾을 수 없습니다 (장애물 확인)");
      }
    } catch {
      setStatus("백엔드 연결 실패");
    } finally {
      setLoading(false);
    }
  }, [mapData, robotPos]);

  // ── LIMO 이동 실행 ──────────────────────────────────
  const handleMove = useCallback(async () => {
    if (path.length < 2) return;
    setMoving(true);
    setStatus("LIMO 이동 명령 전송 중...");

    try {
      const res = await fetch(API_PATHEXEC, {
        method:  "POST",
        headers: HEADERS,
        body:    JSON.stringify({ path }),
      });
      const data = await res.json();

      if (data.success) {
        setStatus(`이동 시작 — ${data.points_sent}개 포인트 전송 완료`);
      } else {
        setStatus("전송 실패 — LIMO 연결 확인");
      }
    } catch {
      setStatus("백엔드 연결 실패");
    } finally {
      setMoving(false);
    }
  }, [path]);

  // ── 좌표 변환 헬퍼 ──────────────────────────────────
  function worldToCanvas(wx, wy, meta, scaleX, scaleY) {
    const col = (wx - meta.origin[0]) / meta.resolution;
    const row = meta.height - (wy - meta.origin[1]) / meta.resolution;
    return [col * scaleX, row * scaleY];
  }

  function canvasToWorld(cx, cy, meta) {
    const scaleX = CANVAS_W / meta.width;
    const scaleY = CANVAS_H / meta.height;
    const col = cx / scaleX;
    const row = cy / scaleY;
    const wx  = meta.origin[0] + col * meta.resolution;
    const wy  = meta.origin[1] + (meta.height - row) * meta.resolution;
    return [Math.round(wx * 10) / 10, Math.round(wy * 10) / 10];
  }

  // ── UI ──────────────────────────────────────────────
  return (
    <div style={styles.overlay}>
      <div style={styles.modal}>
        <div style={styles.header}>
          <h2 style={{ margin: 0 }}>Path Planner</h2>
          <button onClick={onClose} style={styles.closeBtn}>✕</button>
        </div>

        <div style={styles.statusBar}>
          {loading ? "⏳ " : "📍 "}{status}
        </div>
        <div style={styles.rosBar}>
          {rosStatus} {robotPos ? `| 로봇: (${robotPos.x.toFixed(2)}, ${robotPos.y.toFixed(2)})` : "| 우클릭으로 시작점 수동 설정"}
        </div>

        <canvas
          ref={canvasRef}
          width={CANVAS_W}
          height={CANVAS_H}
          style={styles.canvas}
          onClick={handleCanvasClick}
          onContextMenu={handleCanvasRightClick}
        />

        <div style={styles.info}>
          <span>🤖 로봇: {robotPos ? `(${robotPos.x.toFixed(2)}, ${robotPos.y.toFixed(2)})` : "미확인"}</span>
          {goal && (
            <span>🎯 목표: ({goal.x.toFixed(1)}, {goal.y.toFixed(1)})</span>
          )}
          {path.length > 0 && (
            <span>📏 경로: {path.length}포인트</span>
          )}
          {path.length >= 2 && (
            <button
              onClick={handleMove}
              disabled={moving}
              style={styles.moveBtn}
            >
              {moving ? "전송 중..." : "🚗 LIMO 이동"}
            </button>
          )}
        </div>

        <div style={styles.legend}>
          <span style={{ color: "#4CAF50" }}>● 로봇</span>
          <span style={{ color: "#f44336" }}>✕ 목표</span>
          <span style={{ color: "#2196F3" }}>— 경로</span>
          <span style={{ color: "#333" }}>■ 장애물</span>
        </div>
      </div>
    </div>
  );
}

const styles = {
  overlay: {
    position: "fixed", inset: 0,
    background: "rgba(0,0,0,0.6)",
    display: "flex", alignItems: "center", justifyContent: "center",
    zIndex: 1000,
  },
  modal: {
    background: "#fff", borderRadius: 12,
    padding: 20, width: 960,
    maxHeight: "95vh", overflowY: "auto",
    display: "flex", flexDirection: "column", gap: 10,
    boxShadow: "0 8px 32px rgba(0,0,0,0.3)",
  },
  header: {
    display: "flex", justifyContent: "space-between", alignItems: "center",
  },
  closeBtn: {
    background: "none", border: "none",
    fontSize: 20, cursor: "pointer", color: "#666",
  },
  statusBar: {
    background: "#f0f4ff", borderRadius: 6,
    padding: "6px 12px", fontSize: 13, color: "#333",
  },
  rosBar: {
    background: "#f0fff0", borderRadius: 6,
    padding: "4px 12px", fontSize: 12, color: "#555",
  },
  canvas: {
    border: "1px solid #ddd", borderRadius: 6,
    cursor: "crosshair", width: "100%",
  },
  info: {
    display: "flex", gap: 20, fontSize: 13, color: "#555",
  },
  legend: {
    display: "flex", gap: 16, fontSize: 12, color: "#888",
  },
  moveBtn: {
    padding: "6px 16px", background: "#4CAF50", color: "#fff",
    border: "none", borderRadius: 6, cursor: "pointer",
    fontSize: 13, fontWeight: "bold",
  },
};
