import React from "react";
import "./modal.css";

const COMMAND_EMOJI = {
  "go straight":      "⬆️",
  "go straight slow": "🐢",
  "go straight fast": "⚡",
  "turn left":        "↰",
  "turn right":       "↱",
  "sharp left":       "↺",
  "sharp right":      "↻",
  "rotate left":      "🔄",
  "rotate right":     "🔃",
  "curve left":       "↖️",
  "curve right":      "↗️",
  "move back":        "⬇️",
  "move back slow":   "🐢⬇️",
  "stop":             "⏹",
};

const MODE_LABEL = {
  move:      { icon: "🤖", text: "이동 명령" },
  trace:     { icon: "🎯", text: "추적 모드" },
  avoid:     { icon: "🛡️", text: "회피 모드" },
  stop_mode: { icon: "⏹", text: "모드 종료" },
};

function LimoModal({ closeModal, data, mode }) {
  const box = {
    background:    mode === "dark" ? "#2a2a2a" : "#f5f5f5",
    color:         mode === "dark" ? "#fff"    : "#000",
    borderRadius:  "8px",
    padding:       "12px 16px",
    marginBottom:  "10px",
    fontFamily:    "Courier New",
    fontSize:      "14px",
  };

  const label = {
    fontWeight:     "bold",
    color:          mode === "dark" ? "#aaa" : "#555",
    marginBottom:   "6px",
    fontSize:       "12px",
    textTransform:  "uppercase",
    letterSpacing:  "0.5px",
  };

  const responseMode = data?.mode || "move";
  const modeInfo     = MODE_LABEL[responseMode] || MODE_LABEL.move;

  return (
    <div className="modalBackground">
      <div
        className={mode === "dark" ? "dark-modalContainer" : "light-modalContainer"}
        style={{ maxWidth: "500px", width: "90%", padding: "20px", maxHeight: "80vh", overflowY: "auto" }}
      >
        <button className="closeModalBtn" onClick={() => closeModal(false)}>X</button>

        <h2 style={{ textAlign: "center", marginBottom: "20px" }}>LIMO 변환 결과</h2>

        {/* 입력 */}
        <div style={box}>
          <div style={label}>입력</div>
          <div style={{ fontSize: "15px" }}>"{data?.input}"</div>
        </div>

        {/* 모드 표시 */}
        <div style={{ ...box, background: mode === "dark" ? "#1a2a3a" : "#e3f2fd" }}>
          <div style={label}>인식된 모드</div>
          <div style={{ fontSize: "16px", fontWeight: "bold" }}>
            {modeInfo.icon} {modeInfo.text}
          </div>
        </div>

        {/* ── move: 명령 시퀀스 ── */}
        {responseMode === "move" && (() => {
          const sequence = data?.sequence || [];
          const success  = data?.limo_success;
          return (
            <>
              <div style={{ ...box, background: "transparent", padding: 0 }}>
                <div style={{ ...label, marginBottom: "8px" }}>
                  명령 시퀀스 ({sequence.length}단계)
                </div>
                {sequence.map((step, idx) => (
                  <div key={idx} style={{
                    ...box,
                    background:    mode === "dark" ? "#1a2a3a" : "#e3f2fd",
                    marginBottom:  "8px",
                    display:       "flex",
                    alignItems:    "center",
                    gap:           "12px",
                  }}>
                    <div style={{
                      width: "24px", height: "24px", borderRadius: "50%",
                      background: "#1976d2", color: "#fff",
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

              <div style={{
                ...box,
                background: success
                  ? (mode === "dark" ? "#1a3a1a" : "#e8f5e9")
                  : (mode === "dark" ? "#3a1a1a" : "#ffebee"),
              }}>
                <div style={{ ...label, color: success ? "#388e3c" : "#c62828" }}>LIMO 전송</div>
                <div style={{ fontWeight: "bold", color: success ? "#4caf50" : "#ef5350" }}>
                  {success ? "✓ 전체 성공" : "✗ 실패 (LIMO 미연결)"}
                </div>
              </div>
            </>
          );
        })()}

        {/* ── trace: 추적 시작 ── */}
        {responseMode === "trace" && (
          <div style={{ ...box, background: mode === "dark" ? "#1a3a1a" : "#e8f5e9" }}>
            <div style={{ ...label, color: "#388e3c" }}>추적 대상</div>
            <div style={{ fontWeight: "bold", fontSize: "16px", color: "#4caf50" }}>
              🎯 {data?.target}
            </div>
            <div style={{ fontSize: "13px", color: mode === "dark" ? "#aaa" : "#666", marginTop: "8px" }}>
              YOLO 추적 모드가 시작됩니다. 정지하려면 "추적 멈춰"를 입력하세요.
            </div>
          </div>
        )}

        {/* ── avoid: 회피 시작 ── */}
        {responseMode === "avoid" && (
          <div style={{ ...box, background: mode === "dark" ? "#1a3a1a" : "#e8f5e9" }}>
            <div style={{ ...label, color: "#388e3c" }}>상태</div>
            <div style={{ fontWeight: "bold", fontSize: "16px", color: "#4caf50" }}>
              🛡️ 자율 회피 모드 시작
            </div>
            <div style={{ fontSize: "13px", color: mode === "dark" ? "#aaa" : "#666", marginTop: "8px" }}>
              장애물을 감지하며 자동으로 회피합니다. 정지하려면 "모드 종료"를 입력하세요.
            </div>
          </div>
        )}

        {/* ── stop_mode: 모드 종료 ── */}
        {responseMode === "stop_mode" && (
          <div style={{ ...box, background: mode === "dark" ? "#3a1a1a" : "#fff3e0" }}>
            <div style={{ ...label, color: "#e65100" }}>상태</div>
            <div style={{ fontWeight: "bold", fontSize: "16px", color: "#ff9800" }}>
              ⏹ 모든 자율 모드 종료
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default LimoModal;
