import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Trophy, Music, Star } from 'lucide-react';
import './LeaderboardPage.css';

const LeaderboardPage = () => {
    const [leaderboard, setLeaderboard] = useState({ casual: [], competition: [] });
    const [activeTab, setActiveTab] = useState('casual');
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchLeaderboard();
        // Refresh every 10s
        const interval = setInterval(fetchLeaderboard, 10000);
        return () => clearInterval(interval);
    }, []);

    const fetchLeaderboard = async () => {
        try {
            const res = await axios.get('/api/leaderboard');
            setLeaderboard(res.data);
            setLoading(false);
        } catch (err) {
            console.error("Failed to fetch leaderboard", err);
            setLoading(false);
        }
    };

    const currentList = activeTab === 'casual' ? leaderboard.casual : leaderboard.competition;

    return (
        <div className="leaderboard-container">
            <h1 className="text-glow-gold leaderboard-title">
                <Trophy size={40} className="title-icon" />
                Global Leaderboard
            </h1>

            <div className="leaderboard-tabs">
                <button
                    className={`tab-btn ${activeTab === 'casual' ? 'active' : ''}`}
                    onClick={() => setActiveTab('casual')}
                >
                    Casual Mode
                </button>
                <button
                    className={`tab-btn competition ${activeTab === 'competition' ? 'active' : ''}`}
                    onClick={() => setActiveTab('competition')}
                >
                    Competition Mode
                </button>
            </div>

            <div className="leaderboard-table-container box-glow">
                {loading ? (
                    <div className="loading">Loading scores...</div>
                ) : currentList.length === 0 ? (
                    <div className="empty-state">No scores yet. Be the first!</div>
                ) : (
                    <table className="leaderboard-table">
                        <thead>
                            <tr>
                                <th>Rank</th>
                                <th>Singer</th>
                                <th>Song</th>
                                <th>Score</th>
                                <th>Date</th>
                            </tr>
                        </thead>
                        <tbody>
                            {currentList.map((entry, index) => (
                                <tr key={index} className={index < 3 ? `top-${index + 1}` : ''}>
                                    <td className="rank-cell">
                                        {index === 0 && <Star size={16} fill="gold" color="gold" />}
                                        {index + 1}
                                    </td>
                                    <td className="singer-cell">{entry.user_name}</td>
                                    <td className="song-cell">
                                        <Music size={14} style={{ marginRight: 8 }} />
                                        {entry.song}
                                    </td>
                                    <td className="score-cell">{entry.score.toLocaleString()}</td>
                                    <td className="date-cell">
                                        {entry.timestamp ? new Date(entry.timestamp).toLocaleDateString() : '-'}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
};

export default LeaderboardPage;
