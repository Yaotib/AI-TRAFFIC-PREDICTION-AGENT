import { useState } from 'react';
import Chatbot from './Chatbot.jsx';
import DetailsPanel from './DetailsPanel.jsx';

export default function SplitView({
  search,
  plan,
  setPlan,
  m,
  ready,
  sel,
  selId,
  onPick,
  messages,
  onSendMessage,
  onBack,
  onViewMap,
  onStartNavigation,
  onPlanManually,
}) {
  const [mobileTab, setMobileTab] = useState('chat'); // 'chat' | 'details'

  return (
    <div className="split-view-container">
      {/* Mobile Tab Switcher */}
      <div className="split-mobile-tabs">
        <button
          type="button"
          className={`split-tab-btn ${mobileTab === 'chat' ? 'active' : ''}`}
          onClick={() => setMobileTab('chat')}
        >
          💬 Chat Assistant
        </button>
        <button
          type="button"
          className={`split-tab-btn ${mobileTab === 'details' ? 'active' : ''}`}
          onClick={() => setMobileTab('details')}
        >
          📋 Trip Details
        </button>
      </div>

      <div className="split-columns">
        {/* Left Column: Chatbot Panel */}
        <div className={`split-col chat-col ${mobileTab === 'chat' ? 'show-mobile' : 'hide-mobile'}`}>
          <Chatbot
            place={search?.destination}
            fromName={search?.from}
            plan={plan}
            onPlanChange={setPlan}
            messages={messages}
            onSendMessage={onSendMessage}
            isFullPane={true}
            onClose={onBack}
            onPlanManually={onPlanManually}
          />
        </div>

        {/* Right Column: Details Panel */}
        <div className={`split-col details-col ${mobileTab === 'details' ? 'show-mobile' : 'hide-mobile'}`}>
          <div className="details-col-card">
            <DetailsPanel
              m={m}
              ready={ready}
              plan={plan}
              setPlan={setPlan}
              sel={sel}
              selId={selId}
              onPick={onPick}
              search={search}
              onBack={onBack}
              onViewMap={onViewMap}
              onStartNavigation={onStartNavigation}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
