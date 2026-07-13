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
  move:      { icon: "🤖", text: "Move Command" },
  trace:     { icon: "🎯", text: "Trace Mode" },
  avoid:     { icon: "🛡️", text: "Avoid Mode" },
  greet:     { icon: "👋", text: "Greet Mode" },
  stop_mode: { icon: "⏹", text: "Mode Stopped" },
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

        <h2 style={{ textAlign: "center", marginBottom: "20px" }}>LIMO Command Result</h2>

        {/* input */}
        <div style={box}>
          <div style={label}>Input</div>
          <div style={{ fontSize: "15px" }}>"{data?.input}"</div>
        </div>

        {/* recognized mode */}
        <div style={{ ...box, background: mode === "dark" ? "#1a2a3a" : "#e3f2fd" }}>
          <div style={label}>Recognized Mode</div>
          <div style={{ fontSize: "16px", fontWeight: "bold" }}>
            {modeInfo.icon} {modeInfo.text}
          </div>
        </div>

        {/* ── move: command sequence ── */}
        {responseMode === "move" && (() => {
          const sequence = data?.sequence || [];
          const success  = data?.limo_success;
          return (
            <>
              <div style={{ ...box, background: "transparent", padding: 0 }}>
                <div style={{ ...label, marginBottom: "8px" }}>
                  Command Sequence ({sequence.length} steps)
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
                <div style={{ ...label, color: success ? "#388e3c" : "#c62828" }}>LIMO Transmission</div>
                <div style={{ fontWeight: "bold", color: success ? "#4caf50" : "#ef5350" }}>
                  {success ? "✓ All steps succeeded" : "✗ Failed (LIMO not connected)"}
                </div>
              </div>
            </>
          );
        })()}

        {/* ── trace: tracking started ── */}
        {responseMode === "trace" && (
          <div style={{ ...box, background: mode === "dark" ? "#1a3a1a" : "#e8f5e9" }}>
            <div style={{ ...label, color: "#388e3c" }}>Trace Target</div>
            <div style={{ fontWeight: "bold", fontSize: "16px", color: "#4caf50" }}>
              🎯 {data?.target}
            </div>
            <div style={{ fontSize: "13px", color: mode === "dark" ? "#aaa" : "#666", marginTop: "8px" }}>
              YOLO trace mode is starting. Enter "stop tracking" to stop.
            </div>
          </div>
        )}

        {/* ── avoid: avoidance started ── */}
        {responseMode === "avoid" && (
          <div style={{ ...box, background: mode === "dark" ? "#1a3a1a" : "#e8f5e9" }}>
            <div style={{ ...label, color: "#388e3c" }}>Status</div>
            <div style={{ fontWeight: "bold", fontSize: "16px", color: "#4caf50" }}>
              🛡️ Autonomous avoidance mode started
            </div>
            <div style={{ fontSize: "13px", color: mode === "dark" ? "#aaa" : "#666", marginTop: "8px" }}>
              Detecting and avoiding obstacles automatically. Enter "end mode" to stop.
            </div>
          </div>
        )}

        {/* ── greet: greet mode ── */}
        {responseMode === "greet" && (
          <div style={{ ...box, background: mode === "dark" ? "#1a2a3a" : "#e8eaf6" }}>
            <div style={{ ...label, color: "#3949ab" }}>Greet Mode</div>
            <div style={{ fontWeight: "bold", fontSize: "15px", color: "#3f51b5", marginBottom: "8px" }}>
              👋 Searching for a person
            </div>
            <div style={{ fontSize: "13px", color: mode === "dark" ? "#aaa" : "#666" }}>
              Proceeds through SEARCHING → ALIGNING → APPROACHING → GREETING.<br/>
              Enter "end mode" to stop.
            </div>
          </div>
        )}

        {/* ── stop_mode: mode stopped ── */}
        {responseMode === "stop_mode" && (
          <div style={{ ...box, background: mode === "dark" ? "#3a1a1a" : "#fff3e0" }}>
            <div style={{ ...label, color: "#e65100" }}>Status</div>
            <div style={{ fontWeight: "bold", fontSize: "16px", color: "#ff9800" }}>
              ⏹ All autonomous modes stopped
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default LimoModal;
