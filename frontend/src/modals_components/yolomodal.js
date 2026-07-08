import React, { useState, useEffect, useRef } from "react";
import "./modal.css";

const POSITION_EMOJI = { left: "⬅️", right: "➡️", center: "⬆️" };
const COMMAND_EMOJI  = { "go straight": "⬆️", "turn left": "↰", "turn right": "↱", stop: "⏹" };

function YoloModal({ closeModal, mode }) {
  const [running, setRunning]     = useState(false);
  const [detection, setDetection] = useState(null);
  const [loading, setLoading]     = useState(false);
  const pollRef = useRef(null);

  const API = "http://127.0.0.1:8000/api/limo/yolo/";

  const tick = async () => {
    if (!running) return;
    try {
      const res  = await fetch(API, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "tick" }),
      });
      const data = await res.json();
      setDetection(data.detection);
    } catch (_) {}
  };

  const fetchStatus = async () => {
    try {
      const res  = await fetch(API);
      const data = await res.json();
      setRunning(data.running);
      setDetection(data.detection);
    } catch (_) {}
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  useEffect(() => {
    if (running) {
      pollRef.current = setInterval(tick, 600);
    } else {
      clearInterval(pollRef.current);
    }
    return () => clearInterval(pollRef.current);
  }, [running]);

  const handleStart = async () => {
    setLoading(true);
    await fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "start" }),
    });
    setRunning(true);
    setLoading(false);
  };

  const handleStop = async () => {
    setLoading(true);
    await fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "stop" }),
    });
    setRunning(false);
    setLoading(false);
  };

  const boxStyle = {
    background:   mode === "dark" ? "#2a2a2a" : "#f5f5f5",
    color:        mode === "dark" ? "#fff"    : "#000",
    borderRadius: "8px",
    padding:      "12px 16px",
    marginBottom: "10px",
    fontFamily:   "Courier New",
    fontSize:     "14px",
  };

  const labelStyle = {
    fontWeight:    "bold",
    color:         mode === "dark" ? "#aaa" : "#555",
    marginBottom:  "6px",
    fontSize:      "12px",
    textTransform: "uppercase",
    letterSpacing: "0.5px",
  };

  return (
    <div className="modalBackground">
      <div
        className={mode === "dark" ? "dark-modalContainer" : "light-modalContainer"}
        style={{ maxWidth: "420px", width: "90%", padding: "24px" }}
      >
        <button className="closeModalBtn" onClick={() => closeModal(false)}>X</button>

        <h2 style={{ textAlign: "center", marginBottom: "20px" }}>YOLO 자율회피</h2>

        {/* 상태 표시 */}
        <div style={{
          ...boxStyle,
          background: running
            ? (mode === "dark" ? "#1a3a1a" : "#e8f5e9")
            : (mode === "dark" ? "#3a1a1a" : "#ffebee"),
          textAlign: "center",
          fontSize: "16px",
          fontWeight: "bold",
          color: running ? "#4caf50" : "#ef5350",
        }}>
          {running ? "● 실행 중" : "● 정지"}
        </div>

        {/* 탐지 결과 */}
        <div style={boxStyle}>
          <div style={labelStyle}>탐지 결과</div>
          {detection?.class ? (
            <>
              <div>객체: <b>{detection.class}</b> ({(detection.confidence * 100).toFixed(0)}%)</div>
              <div>위치: {POSITION_EMOJI[detection.position]} {detection.position}</div>
              <div>명령: {COMMAND_EMOJI[detection.command]} {detection.command}</div>
            </>
          ) : (
            <div style={{ color: mode === "dark" ? "#aaa" : "#999" }}>탐지된 객체 없음 → 직진</div>
          )}
        </div>

        {/* 버튼 */}
        <div style={{ display: "flex", gap: "12px", justifyContent: "center", marginTop: "8px" }}>
          <button
            onClick={handleStart}
            disabled={running || loading}
            className={mode === "dark" ? "dark-button" : "light-button"}
            style={{ background: "#4caf50", color: "#fff", border: "none", opacity: running ? 0.4 : 1 }}
          >
            시작
          </button>
          <button
            onClick={handleStop}
            disabled={!running || loading}
            className={mode === "dark" ? "dark-button" : "light-button"}
            style={{ background: "#ef5350", color: "#fff", border: "none", opacity: !running ? 0.4 : 1 }}
          >
            정지
          </button>
        </div>
      </div>
    </div>
  );
}

export default YoloModal;
