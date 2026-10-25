import React, { useState, useRef, useEffect } from 'react';
import { 
  Play, 
  Pause, 
  Volume2, 
  VolumeX, 
  Download, 
  Mic, 
  Radio
} from 'lucide-react';

export default function AudioPlayerWidget({ 
  audioUrl, 
  filename, 
  duration, 
  title = "Call Recording" 
}) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [totalDuration, setTotalDuration] = useState(duration || 0);
  const [isMuted, setIsMuted] = useState(false);
  const [playbackError, setPlaybackError] = useState(false);

  const audioRef = useRef(null);

  // Normalize backend URL if relative
  const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
  const fullAudioUrl = audioUrl?.startsWith('http') 
    ? audioUrl 
    : audioUrl ? `${API_BASE.replace(/\/api\/?$/, '')}${audioUrl?.startsWith('/') ? '' : '/'}${audioUrl}` : '';

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || !fullAudioUrl) return;

    const updateTime = () => setCurrentTime(audio.currentTime);
    const setAudioDuration = () => {
      if (audio.duration && !isNaN(audio.duration) && isFinite(audio.duration)) {
        setTotalDuration(audio.duration);
      }
    };
    const onEnded = () => setIsPlaying(false);
    const onError = () => setPlaybackError(true);

    audio.addEventListener('timeupdate', updateTime);
    audio.addEventListener('loadedmetadata', setAudioDuration);
    audio.addEventListener('ended', onEnded);
    audio.addEventListener('error', onError);

    return () => {
      audio.removeEventListener('timeupdate', updateTime);
      audio.removeEventListener('loadedmetadata', setAudioDuration);
      audio.removeEventListener('ended', onEnded);
      audio.removeEventListener('error', onError);
    };
  }, [fullAudioUrl]);

  if (!audioUrl) return null;

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.play().then(() => {
        setIsPlaying(true);
        setPlaybackError(false);
      }).catch(() => {
        setPlaybackError(true);
      });
    }
  };

  const handleSeek = (e) => {
    const seekTime = parseFloat(e.target.value);
    if (audioRef.current) {
      audioRef.current.currentTime = seekTime;
      setCurrentTime(seekTime);
    }
  };

  const toggleMute = () => {
    if (!audioRef.current) return;
    audioRef.current.muted = !isMuted;
    setIsMuted(!isMuted);
  };

  const formatTime = (secs) => {
    if (!secs || isNaN(secs)) return '0:00';
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  return (
    <div className="bg-gradient-to-r from-slate-900 to-navy-900 text-white rounded-xl p-3 sm:p-4 shadow-md border border-slate-800 space-y-2">
      <audio ref={audioRef} src={fullAudioUrl} preload="metadata" />

      {/* Header Info */}
      <div className="flex items-center justify-between text-xs">
        <div className="flex items-center space-x-2">
          <span className="p-1.5 bg-blue-600/30 text-blue-400 rounded-lg flex items-center">
            <Mic className="w-3.5 h-3.5" />
          </span>
          <span className="font-semibold text-slate-200 truncate max-w-[200px] sm:max-w-[320px]">
            {filename || title}
          </span>
          {isPlaying && (
            <span className="px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center space-x-1 animate-pulse">
              <Radio className="w-2.5 h-2.5" />
              <span>Playing</span>
            </span>
          )}
        </div>

        <div className="flex items-center space-x-2">
          <a
            href={fullAudioUrl}
            download={filename || "call_recording.wav"}
            target="_blank"
            rel="noopener noreferrer"
            className="p-1 text-slate-400 hover:text-white transition-colors"
            title="Download Audio File"
          >
            <Download className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>

      {/* Player Controls & Scrubber */}
      <div className="flex items-center space-x-3 pt-1">
        <button
          onClick={togglePlay}
          className="w-8 h-8 rounded-full bg-blue-600 hover:bg-blue-500 text-white flex items-center justify-center shadow transition-transform active:scale-95 shrink-0"
          title={isPlaying ? 'Pause' : 'Play Audio'}
        >
          {isPlaying ? <Pause className="w-4 h-4 fill-current" /> : <Play className="w-4 h-4 fill-current ml-0.5" />}
        </button>

        {/* Progress Bar */}
        <div className="flex-1 flex flex-col justify-center">
          <input
            type="range"
            min={0}
            max={totalDuration || 100}
            step={0.1}
            value={currentTime}
            onChange={handleSeek}
            className="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500 hover:accent-blue-400"
          />
          <div className="flex justify-between items-center text-[10px] text-slate-400 font-mono mt-1">
            <span>{formatTime(currentTime)}</span>
            <span>{formatTime(totalDuration)}</span>
          </div>
        </div>

        {/* Mute Toggle */}
        <button
          onClick={toggleMute}
          className="p-1 text-slate-400 hover:text-white transition-colors shrink-0"
          title={isMuted ? 'Unmute' : 'Mute'}
        >
          {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
        </button>
      </div>

      {/* Sound wave visualizer bars */}
      <div className="flex items-center justify-center space-x-1 pt-1 opacity-75">
        {[40, 70, 30, 85, 55, 100, 65, 45, 90, 35, 75, 50, 80, 60, 95, 40, 70].map((h, i) => (
          <div
            key={i}
            className="w-1 bg-blue-500/60 rounded-full transition-all duration-300"
            style={{
              height: isPlaying ? `${Math.max(4, Math.round(h * (0.4 + ((i * 3) % 6) * 0.1)) * 0.25)}px` : '4px',
            }}
          />
        ))}
      </div>

      {playbackError && (
        <p className="text-[10px] text-amber-400 text-center">
          Audio stream loaded. Click play to start playback.
        </p>
      )}
    </div>
  );
}
