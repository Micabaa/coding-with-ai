import React from 'react';
import { NavLink } from 'react-router-dom';
import { Mic, Trophy, Flame, User } from 'lucide-react';
import './NavBar.css';

const NavBar = () => {
    return (
        <nav className="navbar">
            <div className="navbar-logo text-glow-magenta">
                KaraOKAI
            </div>
            <div className="navbar-links">
                <NavLink to="/" className={({ isActive }) => isActive ? "nav-item active" : "nav-item"}>
                    <Mic size={20} />
                    <span>Singing</span>
                </NavLink>
                <NavLink to="/leaderboard" className={({ isActive }) => isActive ? "nav-item active" : "nav-item"}>
                    <Trophy size={20} />
                    <span>Leaderboard</span>
                </NavLink>
                <NavLink to="/competition" className={({ isActive }) => isActive ? "nav-item active competition" : "nav-item competition"}>
                    <Flame size={20} />
                    <span>Competition</span>
                </NavLink>
            </div>
            <div className="navbar-profile">
                <NavLink to="/profile" className={({ isActive }) => isActive ? "nav-item active" : "nav-item"}>
                    <User size={20} />
                    <span>Profile</span>
                </NavLink>
            </div>
        </nav>
    );
};

export default NavBar;
