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
    marginBottom: "10px",
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

  const sequence = data?.sequence || [];
  const success  = data?.limo_success;

  return (
    <div className="modalBackground">
      <div
        className={mode === "dark" ? "dark-modalContainer" : "light-modalContainer"}
        style={{ maxWidth: "500px", width: "90%", padding: "20px", maxHeight: "80vh", overflowY: "auto" }}
      >
        <button className="closeModalBtn" onClick={() => closeModal(false)}>X</button>

        <h2 style={{ textAlign: "center", marginBottom: "20px" }}>LIMO 변환 결과</h2>

        {/* 입력 */}
        <div style={boxStyle}>
          <div style={labelStyle}>입력</div>
          <div style={{ fontSize: "15px" }}>"{data?.input}"</div>
        </div>

        {/* 시퀀스 */}
        <div style={{ ...boxStyle, background: "transparent", padding: 0 }}>
          <div style={{ ...labelStyle, marginBottom: "8px" }}>
            명령 시퀀스 ({sequence.length}단계)
          </div>
          {sequence.map((step, idx) => (
            <div key={idx} style={{
              ...boxStyle,
              background: mode === "dark" ? "#1a2a3a" : "#e3f2fd",
              marginBottom: "8px",
              display: "flex",
              alignItems: "center",
              gap: "12px",
            }}>
              <div style={{
                width: "24px", height: "24px",
                borderRadius: "50%",
                background: "#1976d2",
                color: "#fff",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: "12px", fontWeight: "bold", flexShrink: 0,
              }}>
                {idx + 1}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: "bold", fontSize: "15px" }}>
                  {COMMAND_EMOJI[step.command] || ""} {step.command}
                </div>
                <div style={{ color: mode === "dark" ? "#aaa" : "#666", fontSize: "12px", marginTop: "2px" }}>
                  linear.x: {step.cmd_vel?.linear?.x} &nbsp;|&nbsp;
                  angular.z: {step.cmd_vel?.angular?.z} &nbsp;|&nbsp;
                  {step.duration}s
                </div>
              </div>
              <div style={{ color: step.success ? "#4caf50" : "#ef5350", fontSize: "18px" }}>
                {step.success ? "✓" : "✗"}
              </div>
            </div>
          ))}
        </div>

        {/* 전체 결과 */}
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
            {success ? "✓ 전체 성공" : "✗ 실패 (LIMO 미연결)"}
          </div>
        </div>
      </div>
    </div>
  );
}

export default LimoModal;
