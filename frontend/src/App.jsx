import { useState } from 'react'
import './App.css'
import LiveKitModal from './components/LiveKitModal';

function App() {
  const [showSupport, setShowSupport] = useState(false);

  const handleSupportClick = () => {
    setShowSupport(true)
  }

  return (
    <div className="app">
      <header className="header">
        <div className="logo">EchoHealth</div>
      </header>

      <main>
        <section className="hero">
          <h1>EchoHealth: A Safe Voice Companion for Reliable Medical Information</h1>
          <div className="search-bar">
            <input type="text" placeholder='Use the assistant to speak your question'></input>
            <button disabled>Search</button>
          </div>
        </section>

        <button className="support-button" onClick={handleSupportClick}>
          Open EchoHealth Assistant
        </button>
      </main>

      {showSupport && <LiveKitModal setShowSupport={setShowSupport}/>}
    </div>
  )
}

export default App