import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Send, User, Bot, Loader } from 'lucide-react';
import './ChatPage.css';

const ChatPage = () => {
    const [messages, setMessages] = useState([
        { role: 'assistant', content: "Hello! I'm your KaraOKAI Host. Ask me to play a song, or just chat!" }
    ]);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef(null);

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
            const res = await axios.post('/api/chat', { message: userMsg });
            const { response, action } = res.data;

            setMessages(prev => [...prev, { role: 'assistant', content: response }]);

            if (action && action.type === 'play_audio') {
                // Determine if we should redirect or just notify
                // For now, let's notify the user they can go to the singing page
                // Or we could auto-navigate?
                // The user request didn't specify auto-play from chat, but implied it.
                // Let's just append a message about the action.
                setMessages(prev => [...prev, { role: 'system', content: `🎵 I found "${action.payload.track}". Go to the Singing page to perform it!` }]);
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
                                <div className="msg-content">{msg.content}</div>
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
