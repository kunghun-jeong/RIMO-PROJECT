import React, { useState } from "react";
import "./group-forms.css";
import LimoModal from "./limomodal";

function NaturalIntentForm({ mode, closeNaturalModal }) {
  const [inputText, setInputText] = useState("");
  const [limoData, setLimoData] = useState(null);
  const [showLimoModal, setShowLimoModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!inputText.trim()) {
      setError("명령을 입력하세요.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await fetch("http://127.0.0.1:8000/api/limo/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: inputText }),
      });

      const data = await response.json();
      setLimoData(data);
      setShowLimoModal(true);
    } catch (err) {
      console.error(err);
      setError("서버 연결에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ margin: "20px", minWidth: "400px" }}>
      <h3 style={{ marginBottom: "16px" }}>자연어로 LIMO 제어</h3>

      <p style={{ fontSize: "13px", color: mode === "dark" ? "#aaa" : "#666", marginBottom: "16px" }}>
        예시: "앞으로 가줘", "왼쪽으로 돌아", "멈춰", "go forward for 3 seconds"
      </p>

      <form onSubmit={handleSubmit}>
        <textarea
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="자연어 명령을 입력하세요..."
          rows={4}
          style={{
            width: "100%",
            padding: "10px",
            fontSize: "15px",
            borderRadius: "8px",
            border: "1px solid #ccc",
            resize: "vertical",
            boxSizing: "border-box",
            background: mode === "dark" ? "#444" : "#fff",
            color: mode === "dark" ? "#fff" : "#000",
          }}
        />

        {error && (
          <p style={{ color: "crimson", fontSize: "13px", marginTop: "6px" }}>{error}</p>
        )}

        <footer className="footer" style={{ marginTop: "16px" }}>
          <button
            type="submit"
            disabled={loading}
            className={mode === "dark" ? "dark-button" : "light-button"}
          >
            {loading ? "처리 중..." : "전송"}
          </button>
        </footer>
      </form>

      {showLimoModal && (
        <LimoModal
          closeModal={setShowLimoModal}
          data={limoData}
          mode={mode}
        />
      )}
    </div>
  );
}

export default NaturalIntentForm;
