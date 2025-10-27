import { useState, useCallback } from "react";
import { LiveKitRoom, RoomAudioRenderer } from "@livekit/components-react";
import "@livekit/components-styles";
import SimpleVoiceAssistant from "./SimpleVoiceAssistant";

const LiveKitModal = ({ setShowSupport }) => {
  const [isSubmittingName, setIsSubmittingName] = useState(true);
  const [name, setName] = useState("");
  const [token, setToken] = useState(null);

  const getToken = useCallback(async (userName) => {
    try {
      const response = await fetch(
        `/api/getToken?name=${encodeURIComponent(userName)}&room=health-room`
      );
      const t = await response.text();
      setToken(t);
      setIsSubmittingName(false);
    } catch (error) {
      console.error(error);
    }
  }, []);

  const handleNameSubmit = (e) => {
    e.preventDefault();
    if (name.trim()) {
      getToken(name);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <div className="modal-header">
          <div className="modal-title">
            <div className="modal-icon">🏥</div>
            <span>EchoHealth Assistant</span>
          </div>
          <button
            className="modal-close"
            onClick={() => setShowSupport(false)}
          >
            ✕
          </button>
        </div>
        
        <div className="support-room">
          {isSubmittingName ? (
            <form onSubmit={handleNameSubmit} className="name-form">
              <div className="form-content">
                <h2>Connect to EchoHealth</h2>
                <p className="form-description">
                  Enter your name to start a voice conversation with our medical information assistant
                </p>
                <div className="input-group">
                  <label htmlFor="name">Your Name</label>
                  <input
                    id="name"
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Enter your name"
                    required
                    autoFocus
                  />
                </div>
                <div className="button-group">
                  <button type="submit" className="connect-button">
                    <span className="button-icon">🚀</span>
                    Connect & Start
                  </button>
                  <button
                    type="button"
                    className="cancel-button"
                    onClick={() => setShowSupport(false)}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </form>
          ) : token ? (
            <LiveKitRoom
              serverUrl={import.meta.env.VITE_LIVEKIT_URL}
              token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NjE1OTU3NDMsImlkZW50aXR5IjoiUGFyaXRvc2giLCJpc3MiOiJBUElFcjJnMzJab1lrOW8iLCJuYmYiOjE3NjE1OTQ4NDMsInN1YiI6IlBhcml0b3NoIiwidmlkZW8iOnsiY2FuUHVibGlzaCI6dHJ1ZSwiY2FuUHVibGlzaERhdGEiOnRydWUsImNhblN1YnNjcmliZSI6dHJ1ZSwicm9vbSI6InJvb20xIiwicm9vbUpvaW4iOnRydWV9fQ.lKkDjcXGMNDvTezCXfu-7UZhojl-XajkU6uPjTIv4m8"
              connect={true}
              video={false}
              audio={true}
              onDisconnected={() => {
                setShowSupport(false);
                setIsSubmittingName(true);
                setToken(null);
              }}
            >
              <RoomAudioRenderer />
              <SimpleVoiceAssistant />
            </LiveKitRoom>
          ) : null}
        </div>
      </div>
    </div>
  );
};

export default LiveKitModal;