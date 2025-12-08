import React, { useState, useEffect } from 'react';
import { User, Save } from 'lucide-react';
import './ProfilePage.css';

const ProfilePage = () => {
    const [name, setName] = useState('');
    const [saved, setSaved] = useState(false);

    useEffect(() => {
        const storedName = localStorage.getItem('karaoke_user_name');
        if (storedName) setName(storedName);
    }, []);

    const handleSave = () => {
        if (name.trim()) {
            localStorage.setItem('karaoke_user_name', name.trim());
            setSaved(true);
            setTimeout(() => setSaved(false), 2000);
        }
    };

    return (
        <div className="profile-container">
            <div className="profile-card box-glow">
                <User size={64} className="profile-icon" />
                <h1 className="text-glow-magenta">My Profile</h1>

                <div className="input-group">
                    <label>Stage Name</label>
                    <input
                        type="text"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="Enter your name"
                    />
                </div>

                <button className="save-btn" onClick={handleSave}>
                    <Save size={18} />
                    Save Profile
                </button>

                {saved && <p className="success-msg text-glow-cyan">Profile Saved!</p>}
            </div>
        </div>
    );
};

export default ProfilePage;
