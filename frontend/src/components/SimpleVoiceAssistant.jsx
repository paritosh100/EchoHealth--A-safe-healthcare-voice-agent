import {
  useVoiceAssistant,
  BarVisualizer,
  VoiceAssistantControlBar,
  useTrackTranscription,
  useLocalParticipant,
} from "@livekit/components-react";
import { Track } from "livekit-client";
import { useEffect, useState } from "react";
import "./SimpleVoiceAssistant.css";

const Message = ({ type, text }) => {
  return (
    <div className={`message message-${type}`}>
      <div className="message-header">
        <div className={`message-avatar ${type}`}>
          {type === "agent" ? "🏥" : "👤"}
        </div>
        <div className="message-info">
          <span className="message-sender">
            {type === "agent" ? "EchoHealth Assistant" : "You"}
          </span>
          <span className="message-time">
            {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>
      </div>
      <div className="message-content">
        <span className="message-text">{text}</span>
      </div>
    </div>
  );
};

const SimpleVoiceAssistant = () => {
  const { state, audioTrack, agentTranscriptions } = useVoiceAssistant();
  const localParticipant = useLocalParticipant();
  const { segments: userTranscriptions } = useTrackTranscription({
    publication: localParticipant.microphoneTrack,
    source: Track.Source.Microphone,
    participant: localParticipant.localParticipant,
  });

  const [messages, setMessages] = useState([]);

  useEffect(() => {
    const allMessages = [
      ...(agentTranscriptions?.map((t) => ({ ...t, type: "agent" })) ?? []),
      ...(userTranscriptions?.map((t) => ({ ...t, type: "user" })) ?? []),
    ].sort((a, b) => a.firstReceivedTime - b.firstReceivedTime);
    setMessages(allMessages);
  }, [agentTranscriptions, userTranscriptions]);

  return (
    <div className="voice-assistant-container">
      {/* Left Pane - Voice Controls */}
      <div className="left-pane">
        <div className="voice-controls-section">
          <div className="assistant-header">
            <div className="status-section">
              <div className={`status-indicator ${state}`}>
                <div className="status-dot"></div>
                <span className="status-text">
                  {state === 'listening' ? 'Listening...' : 
                   state === 'speaking' ? 'Speaking...' : 
                   state === 'thinking' ? 'Thinking...' : 'Ready'}
                </span>
              </div>
            </div>
          </div>

          <div className="visualizer-section">
            <div className="visualizer-container">
              <BarVisualizer state={state} barCount={12} trackRef={audioTrack} />
            </div>
          </div>

          <div className="control-section">
            <VoiceAssistantControlBar />
          </div>
        </div>
      </div>

      {/* Right Pane - Chat Conversation */}
      <div className="right-pane">
        <div className="conversation-section">
          <div className="conversation-header">
            <h3>Conversation</h3>
            <div className="conversation-stats">
              {messages.length} messages
            </div>
          </div>
          <div className="conversation">
            {messages.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">💬</div>
                <p>Start speaking to begin your conversation with EchoHealth</p>
              </div>
            ) : (
              messages.map((msg, index) => (
                <Message key={msg.id || index} type={msg.type} text={msg.text} />
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SimpleVoiceAssistant;