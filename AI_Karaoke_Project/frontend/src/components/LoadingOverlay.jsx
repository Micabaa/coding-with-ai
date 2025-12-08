import React from 'react';
import { Loader2 } from 'lucide-react';
import './LoadingOverlay.css'; // We will create this CSS

const LoadingOverlay = ({ message = "Loading..." }) => {
    return (
        <div className="loading-overlay">
            <div className="loading-content box-glow">
                <Loader2 className="loading-spinner" size={48} />
                <h2 className="text-glow-cyan">{message}</h2>
            </div>
        </div>
    );
};

export default LoadingOverlay;
