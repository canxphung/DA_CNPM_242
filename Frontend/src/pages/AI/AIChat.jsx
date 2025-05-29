// src/pages/AI/AIChat.jsx
import React, { useState, useRef, useEffect } from 'react';
import Header from '../../components/Header';
import Footer from '../../components/Footer';
import Sidebar from '../../components/Sidebar';
import aiChatService from '../../utils/aiChatService'; // Updated service
import NotificationToast from '../../components/NotificationToast';
import { Send, Bot, User2, RotateCcw } from 'lucide-react'; // Added RotateCcw for reset
import { useAuth } from '../../contexts/AuthContext';

const AIChat = () => {
  const [message, setMessage] = useState('');
  const [chatHistory, setChatHistory] = useState([]); // { sender, text, actions_by_ai?, intent?, isError?, timestamp }
  const [isLoading, setIsLoading] = useState(false);
  const [notification, setNotification] = useState({ show: false, message: "", type: "success" });
  const { currentUser } = useAuth();

  const chatEndRef = useRef(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [chatHistory]);

  const showToast = (message, type = "success") => {
    setNotification({ show: true, message, type, onClose: () => setNotification(p => ({...p, show: false})) });
  };

  const handleSendMessage = async (e, quickReplyText = null) => {
    if (e) e.preventDefault(); 
    const currentMessage = quickReplyText || message.trim();
    if (!currentMessage) return;

    const userMessageEntry = { sender: 'user', text: currentMessage, timestamp: new Date().toISOString() };
    setChatHistory((prev) => [...prev, userMessageEntry]);
    if(!quickReplyText) setMessage(''); // Clear input only if not from quick reply
    setIsLoading(true);

    try {
      const result = await aiChatService.sendMessage(currentMessage, { userId: currentUser?.id });
      
      if (result.success && result.response) {
        const aiResponseEntry = {
          sender: 'ai',
          text: result.response.text,
          actions_by_ai: result.response.actions_taken_by_ai || [], 
          intent: result.response.intent,
          timestamp: result.response.timestamp || new Date().toISOString(),
        };
        setChatHistory((prev) => [...prev, aiResponseEntry]);
      } else {
        const errorMsg = result.error || "AI không phản hồi hoặc có lỗi.";
        const errorResponseEntry = {
            sender: 'ai',
            text: result.response?.text || errorMsg, 
            isError: true,
            timestamp: new Date().toISOString(),
        };
        setChatHistory(prev => [...prev, errorResponseEntry]);
        showToast(errorMsg, "error");
      }
    } catch (error) { 
      const genericErrorMsg = 'Xin lỗi, đã có lỗi xảy ra khi giao tiếp với AI.';
      setChatHistory((prev) => [...prev, { sender: 'ai', text: genericErrorMsg, isError: true, timestamp: new Date().toISOString() }]);
      showToast(genericErrorMsg, "error");
    } finally {
      setIsLoading(false);
      if(quickReplyText) setMessage(''); // Clear input after quick reply processing
    }
  };
  
  const handleResetChat = () => {
      aiChatService.resetSession();
      setChatHistory([]);
      setMessage('');
      showToast("Cuộc trò chuyện đã được làm mới.", "info");
  }
  
  const quickReplies = [
    "Tình trạng nhà kính hiện tại?",
    "Độ ẩm đất thế nào?",
    "Bật bơm 5 phút được không?",
    "Có khuyến nghị tưới nào không?",
  ];

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex flex-col w-full md:w-5/6 ml-0 md:ml-64">
        <Header />
        {notification.show && notification.onClose && (
          <NotificationToast message={notification.message} type={notification.type} onClose={notification.onClose}/>
        )}
        <main className="flex-grow p-4 sm:p-6 bg-gray-100">
          <div className="flex justify-between items-center mb-6">
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-700 flex items-center">
                <Bot size={30} className="mr-3 text-blue-500"/>AI Chatbot Nhà Kính
            </h1>
            <button 
                onClick={handleResetChat} 
                title="Bắt đầu cuộc trò chuyện mới"
                className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-full transition-colors"
            >
                <RotateCcw size={20}/>
            </button>
          </div>
          

          <div className="flex flex-col h-[calc(100vh-230px)] sm:h-[calc(100vh-260px)] max-w-3xl mx-auto bg-white rounded-xl shadow-2xl overflow-hidden border border-gray-200">
            <div className="flex-grow p-4 overflow-y-auto space-y-4 scroll-smooth">
              {chatHistory.length === 0 && (
                <div className="text-center text-gray-500 mt-10 px-4">
                  <Bot size={48} className="mx-auto text-gray-400 mb-3"/>
                  <p className="text-lg">Chào bạn! Tôi là trợ lý AI của bạn.</p>
                  <p className="text-sm">Hãy hỏi tôi điều gì đó về nhà kính nhé.</p>
                </div>
              )}
              {chatHistory.map((msg, index) => (
                <div key={index} className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}>
                  <div className={`flex items-start max-w-[80%] sm:max-w-[70%] ${msg.sender === 'user' ? 'flex-row-reverse' : ''}`}>
                     {msg.sender === 'ai' && <div className="w-8 h-8 p-1.5 rounded-full bg-blue-500 text-white mr-2 mt-1 flex-shrink-0 flex items-center justify-center shadow"><Bot size={18}/></div>}
                     {msg.sender === 'user' && <div className="w-8 h-8 p-1.5 rounded-full bg-green-500 text-white ml-2 mt-1 flex-shrink-0 flex items-center justify-center shadow"><User2 size={18}/></div>}
                    <div className={`px-3.5 py-2.5 rounded-2xl shadow-sm ${
                      msg.sender === 'user' ? 'bg-blue-500 text-white rounded-br-none' 
                                           : (msg.isError ? 'bg-red-100 text-red-700 rounded-bl-none border border-red-200' : 'bg-gray-100 text-gray-800 rounded-bl-none border border-gray-200')
                    }`}>
                      <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.text}</p>
                      {msg.sender === 'ai' && msg.actions_by_ai && msg.actions_by_ai.length > 0 && (
                        <div className="mt-2 pt-1.5 border-t border-gray-300/50 text-xs text-gray-500">
                          <p className="font-semibold text-gray-700 mb-0.5">AI đã thực hiện/trigger:</p>
                          <ul className="list-disc list-inside pl-1">
                            {msg.actions_by_ai.map((action, i) => <li key={i} className="text-gray-600">{action}</li>)}
                          </ul>
                        </div>
                      )}
                       {msg.sender === 'ai' && msg.intent && msg.intent !== 'unknown' && msg.intent !== 'fallback_error' && !msg.isError && (
                            <p className="text-xs text-blue-500 italic mt-1.5 opacity-80">Intent: {msg.intent}</p>
                       )}
                    </div>
                  </div>
                  <p className={`text-[11px] text-gray-400 mt-1 ${msg.sender === 'user' ? 'mr-10 sm:mr-12' : 'ml-10 sm:ml-12'}`}>
                    {new Date(msg.timestamp).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
              ))}
              {isLoading && (
                <div className="flex items-start justify-start">
                   <div className="flex items-center px-3 py-2 rounded-lg bg-gray-100 text-gray-700 border border-gray-200 animate-pulse">
                     <Bot className="w-5 h-5 mr-2 text-blue-500" />
                     <p className="text-sm">AI đang nghĩ...</p>
                   </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>
            
            {chatHistory.length <= 1 && !isLoading && (
                <div className="p-2.5 border-t border-gray-200 flex flex-wrap gap-1.5 sm:gap-2 justify-center">
                    {quickReplies.map(reply => (
                        <button 
                            key={reply} 
                            onClick={() => handleSendMessage(null, reply)}
                            className="px-2.5 sm:px-3 py-1 sm:py-1.5 bg-blue-50 text-blue-600 rounded-full text-xs hover:bg-blue-100 transition-colors border border-blue-200"
                        >
                            {reply}
                        </button>
                    ))}
                </div>
            )}

            <form onSubmit={handleSendMessage} className="p-3 border-t border-gray-200 flex items-center gap-2 bg-white">
              <input type="text" value={message} onChange={(e) => setMessage(e.target.value)}
                placeholder="Hỏi AI hoặc ra lệnh..."
                className="flex-grow p-2.5 sm:p-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-400 text-sm"
                disabled={isLoading}
                onKeyPress={(e) => { if (e.key === 'Enter' && !e.shiftKey && message.trim()) { e.preventDefault(); handleSendMessage(e);}}}/>
              <button type="submit"
                className="bg-blue-600 hover:bg-blue-700 text-white p-2.5 sm:p-3 rounded-xl flex items-center justify-center transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
                disabled={isLoading || !message.trim()}>
                <Send className="w-5 h-5" />
              </button>
            </form>
          </div>
        </main>
        <Footer />
      </div>
    </div>
  );
};

export default AIChat;