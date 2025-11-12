# audio_analysis_tool.py

import numpy as np
import librosa

class AudioAnalysisTool:
    def __init__(self, audio_file):
        self.audio_file = audio_file
        self.audio_data, self.sample_rate = self.load_audio()

    def load_audio(self):
        audio_data, sample_rate = librosa.load(self.audio_file, sr=None)
        return audio_data, sample_rate

    def detect_pitch(self):
        pitches, magnitudes = librosa.piptrack(y=self.audio_data, sr=self.sample_rate)
        return pitches, magnitudes

    def analyze_timing(self):
        onset_frames = librosa.onset.onset_detect(y=self.audio_data, sr=self.sample_rate)
        return librosa.frames_to_time(onset_frames, sr=self.sample_rate)

    def get_audio_features(self):
        tempo, _ = librosa.beat.beat_track(y=self.audio_data, sr=self.sample_rate)
        return {
            'tempo': tempo,
            'pitch': self.detect_pitch(),
            'timing': self.analyze_timing()
        }