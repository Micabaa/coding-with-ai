import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Send, User, Bot, Loader, Music } from 'lucide-react';
import './ChatPage.css';

const ChatPage = () => {
    const [messages, setMessages] = useState([
        { role: 'assistant', content: "Hello! I'm your KaraOKAI Host. Ask me to play a song, or just chat!" }
    ]);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef(null);
    const navigate = useNavigate();

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSend = async (e) => {
        e.preventDefault();
        if (!input.trim()) return;

        const userMsg = input;
        setInput("");
        setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
        setIsLoading(true);

        try {
            // Prepare history (exclude system messages if any, though backend filters too)
            const history = messages.filter(m => m.role === 'user' || m.role === 'assistant');
            const res = await axios.post('/api/chat', {
                message: userMsg,
                history: history
            });
            const { response, action } = res.data;

            setMessages(prev => [...prev, { role: 'assistant', content: response }]);

            if (action && action.type === 'play_audio') {
                setMessages(prev => [...prev, {
                    role: 'system',
                    content: `🎵 I found "${action.payload.track}". Ready to sing?`,
                    actionData: action.payload
                }]);
            }

        } catch (err) {
            console.error("Chat error:", err);
            setMessages(prev => [...prev, { role: 'assistant', content: "Sorry, I had trouble connecting to the host." }]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="chat-container">
            <h1 className="text-glow-cyan title-large">KaraOKAI Chat</h1>

            <div className="chat-window box-glow">
                <div className="messages-list">
                    {messages.map((msg, idx) => (
                        <div key={idx} className={`message-row ${msg.role}`}>
                            <div className="message-bubble">
                                {msg.role === 'user' && <User size={16} className="msg-icon" />}
                                {msg.role === 'assistant' && <Bot size={16} className="msg-icon" />}
                                <div className="msg-content">
                                    {msg.content}
                                    {msg.actionData && (
                                        <button
                                            className="action-btn"
                                            onClick={() => navigate('/singing', { state: { autoPlaySong: msg.actionData.track } })}
                                        >
                                            <Music size={16} /> Sing "{msg.actionData.track}" Now!
                                        </button>
                                    )}
                                </div>
                            </div>
                        </div>
                    ))}
                    {isLoading && (
                        <div className="message-row assistant">
                            <div className="message-bubble loading">
                                <Loader className="spin" size={16} /> Typing...
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                <form onSubmit={handleSend} className="chat-input-area">
                    <input
                        type="text"
                        placeholder="Talk to the Host..."
                        value={input}
                        onChange={e => setInput(e.target.value)}
                        disabled={isLoading}
                    />
                    <button type="submit" disabled={isLoading || !input.trim()}>
                        <Send size={20} />
                    </button>
                </form>
            </div>
        </div>
    );
};

export default ChatPage;
