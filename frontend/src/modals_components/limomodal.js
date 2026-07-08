import React from "react";
import "./modal.css";

const COMMAND_EMOJI = {
  "go straight": "⬆️",
  "turn left":   "↰",
  "turn right":  "↱",
  "move back":   "⬇️",
  "stop":        "⏹",
};

function LimoModal({ closeModal, data, mode }) {
  const boxStyle = {
    background: mode === "dark" ? "#2a2a2a" : "#f5f5f5",
    color:      mode === "dark" ? "#fff"    : "#000",
    borderRadius: "8px",
    padding: "12px 16px",
    marginBottom: "12px",
    fontFamily: "Courier New",
    fontSize: "14px",
  };

  const labelStyle = {
    fontWeight: "bold",
    color: mode === "dark" ? "#aaa" : "#555",
    marginBottom: "6px",
    fontSize: "12px",
    textTransform: "uppercase",
    letterSpacing: "0.5px",
  };

  const command = data?.command || "unknown";
  const cmdVel  = data?.cmd_vel || null;
  const success = data?.limo_success;

  return (
    <div className="modalBackground">
      <div
        className={mode === "dark" ? "dark-modalContainer" : "light-modalContainer"}
        style={{ maxWidth: "480px", width: "90%", padding: "20px" }}
      >
        <button className="closeModalBtn" onClick={() => closeModal(false)}>X</button>

        <h2 style={{ textAlign: "center", marginBottom: "20px" }}>LIMO 변환 결과</h2>

        {/* 입력 */}
        <div style={boxStyle}>
          <div style={labelStyle}>입력</div>
          <div style={{ fontSize: "15px" }}>"{data?.input}"</div>
        </div>

        {/* 명령 */}
        <div style={{ ...boxStyle, background: mode === "dark" ? "#1a2a3a" : "#e3f2fd" }}>
          <div style={{ ...labelStyle, color: "#1976d2" }}>선택된 명령</div>
          <div style={{ fontSize: "22px", fontWeight: "bold", letterSpacing: "1px" }}>
            {COMMAND_EMOJI[command] || ""} {command}
          </div>
          <div style={{ marginTop: "6px", color: mode === "dark" ? "#aaa" : "#666" }}>
            speed: {data?.speed ?? "-"}  &nbsp;|&nbsp;  duration: {data?.duration ?? "-"}s
          </div>
        </div>

        {/* cmd_vel */}
        <div style={{ ...boxStyle, background: mode === "dark" ? "#1a3a1a" : "#e8f5e9" }}>
          <div style={{ ...labelStyle, color: "#388e3c" }}>cmd_vel (ROS2 Twist)</div>
          {cmdVel ? (
            <>
              <div>linear.x  : {cmdVel.linear.x}</div>
              <div>linear.y  : {cmdVel.linear.y}</div>
              <div>angular.z : {cmdVel.angular.z}</div>
            </>
          ) : (
            <div>변환 불가</div>
          )}
        </div>

        {/* LIMO 전송 결과 */}
        <div style={{
          ...boxStyle,
          background: success
            ? (mode === "dark" ? "#1a3a1a" : "#e8f5e9")
            : (mode === "dark" ? "#3a1a1a" : "#ffebee"),
        }}>
          <div style={{ ...labelStyle, color: success ? "#388e3c" : "#c62828" }}>
            LIMO 전송
          </div>
          <div style={{ fontWeight: "bold", color: success ? "#4caf50" : "#ef5350" }}>
            {success === true ? "✓ 성공" : success === false ? "✗ 실패 (LIMO 미연결)" : "-"}
          </div>
        </div>
      </div>
    </div>
  );
}

export default LimoModal;
