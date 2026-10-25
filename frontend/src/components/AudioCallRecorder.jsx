import React, { useState, useRef, useEffect } from 'react';
import { 
  Mic, 
  Square, 
  Upload, 
  Check, 
  Sparkles, 
  FileAudio, 
  AlertCircle
} from 'lucide-react';

export default function AudioCallRecorder({ onImportAudio, importing }) {
  const [activeMode, setActiveMode] = useState('upload'); // 'upload' | 'record'
  
  // File Upload State
  const [selectedFile, setSelectedFile] = useState(null);
  const [transcriptNotes, setTranscriptNotes] = useState('');

  // Live Microphone Recording State
  const [isRecording, setIsRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [recordedBlob, setRecordedBlob] = useState(null);
  const [recordedUrl, setRecordedUrl] = useState(null);
  const [liveTranscript, setLiveTranscript] = useState('');
  const [recordError, setRecordError] = useState('');

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerRef = useRef(null);
  const recognitionRef = useRef(null);

  // Setup Web Speech API for real-time live preview if supported
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      try {
        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-IN'; // Indian English / fallback

        recognition.onresult = (event) => {
          let fullText = '';
          for (let i = 0; i < event.results.length; i++) {
            fullText += event.results[i][0].transcript + ' ';
          }
          setLiveTranscript(fullText.trim());
        };

        recognition.onerror = (e) => {
          console.debug('Speech recognition event:', e.error);
        };

        recognitionRef.current = recognition;
      } catch (e) {
        console.debug('Speech recognition init note:', e);
      }
    }
  }, []);

  // Cleanup audio preview URLs on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (recordedUrl) URL.revokeObjectURL(recordedUrl);
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
        mediaRecorderRef.current.stop();
      }
    };
  }, [recordedUrl]);

  // Start live microphone recording
  const startRecording = async () => {
    setRecordError('');
    setRecordedBlob(null);
    if (recordedUrl) URL.revokeObjectURL(recordedUrl);
    setRecordedUrl(null);
    setLiveTranscript('');
    audioChunksRef.current = [];

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        setRecordedBlob(audioBlob);
        const url = URL.createObjectURL(audioBlob);
        setRecordedUrl(url);

        // Stop all audio tracks
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorder.start(250);
      setIsRecording(true);
      setRecordingSeconds(0);

      timerRef.current = setInterval(() => {
        setRecordingSeconds((prev) => prev + 1);
      }, 1000);

      // Start speech recognition if supported
      if (recognitionRef.current) {
        try {
          recognitionRef.current.start();
        } catch {
          // ignore already started error
        }
      }
    } catch (err) {
      setRecordError('Could not access microphone: ' + (err.message || 'Permission denied'));
    }
  };

  // Stop live recording
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      if (timerRef.current) clearInterval(timerRef.current);
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch {
          // ignore
        }
      }
    }
  };

  const formatSeconds = (sec) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  // Handle Form Submission
  const handleSubmit = (e) => {
    e.preventDefault();

    if (activeMode === 'upload') {
      if (!selectedFile) {
        alert('Please choose an audio file from your device.');
        return;
      }
      onImportAudio({
        file: selectedFile,
        transcript: transcriptNotes.trim(),
        filename: selectedFile.name,
      });
    } else {
      if (!recordedBlob) {
        alert('Please record a call or voice note first.');
        return;
      }
      const audioFile = new File(
        [recordedBlob], 
        `recorded_call_${new Date().toISOString().slice(0, 10)}.webm`, 
        { type: 'audio/webm' }
      );
      onImportAudio({
        file: audioFile,
        transcript: liveTranscript || transcriptNotes.trim(),
        filename: audioFile.name,
      });
    }
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
      {/* Header and Mode Selector */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
        <div>
          <h4 className="text-sm font-bold text-navy-900 flex items-center space-x-2">
            <Mic className="w-4 h-4 text-blue-600" />
            <span>Call Recording & Audio Analysis</span>
          </h4>
          <p className="text-xs text-slate-500 mt-0.5">
            AI transcribes the call, segments speakers, and extracts key deal terms directly into the agreement.
          </p>
        </div>

        <div className="flex items-center space-x-1 bg-slate-100 p-1 rounded-lg self-start sm:self-auto">
          <button
            type="button"
            onClick={() => setActiveMode('upload')}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all flex items-center space-x-1.5 ${
              activeMode === 'upload' 
                ? 'bg-white text-navy-900 shadow-sm' 
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Upload File</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveMode('record')}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all flex items-center space-x-1.5 ${
              activeMode === 'record' 
                ? 'bg-white text-navy-900 shadow-sm' 
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Mic className="w-3.5 h-3.5 text-red-500" />
            <span>Record Live Mic</span>
          </button>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* MODE 1: FILE UPLOAD */}
        {activeMode === 'upload' && (
          <div className="space-y-3">
            <div className="border-2 border-dashed border-slate-200 hover:border-blue-400 rounded-xl p-5 text-center transition-colors bg-slate-50/50">
              <input
                id="call-audio-file-input"
                type="file"
                accept="audio/*,.mp3,.wav,.m4a,.aac,.ogg,.webm"
                className="hidden"
                onChange={(e) => setSelectedFile(e.target.files[0] || null)}
              />
              <label 
                htmlFor="call-audio-file-input" 
                className="cursor-pointer flex flex-col items-center justify-center space-y-2"
              >
                <div className="w-10 h-10 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center">
                  <FileAudio className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-xs font-bold text-navy-900 hover:underline">
                    {selectedFile ? selectedFile.name : 'Click to select call recording'}
                  </span>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    Supports MP3, WAV, M4A, AAC, WEBM, OGG (Max 25MB)
                  </p>
                </div>
              </label>

              {selectedFile && (
                <div className="mt-3 flex items-center justify-center space-x-3 text-xs">
                  <span className="text-emerald-700 font-semibold flex items-center space-x-1">
                    <Check className="w-3.5 h-3.5" />
                    <span>File Selected ({(selectedFile.size / (1024 * 1024)).toFixed(2)} MB)</span>
                  </span>
                  <button
                    type="button"
                    onClick={() => setSelectedFile(null)}
                    className="text-red-600 hover:underline text-[11px]"
                  >
                    Change
                  </button>
                </div>
              )}
            </div>

            <div>
              <label className="block text-[11px] font-bold text-slate-700 mb-1">
                Transcript or Dialogue Summary (Optional / Auto-generated if blank):
              </label>
              <textarea
                rows={2}
                placeholder="Example: Rajesh called to agree on ₹50,000 milestones with 2-week delivery."
                value={transcriptNotes}
                onChange={(e) => setTranscriptNotes(e.target.value)}
                className="w-full p-2.5 text-xs border border-slate-300 rounded-lg outline-none focus:ring-1 focus:ring-navy-900"
              />
            </div>
          </div>
        )}

        {/* MODE 2: LIVE MICROPHONE RECORDING */}
        {activeMode === 'record' && (
          <div className="space-y-4">
            <div className="p-5 bg-slate-50 rounded-xl border border-slate-200 text-center space-y-3">
              <div className="flex items-center justify-center space-x-3">
                {!isRecording ? (
                  <button
                    type="button"
                    onClick={startRecording}
                    className="px-5 py-2.5 bg-red-600 hover:bg-red-700 text-white text-xs font-bold rounded-full shadow-md flex items-center space-x-2 transition-transform active:scale-95"
                  >
                    <Mic className="w-4 h-4 animate-pulse" />
                    <span>Start Microphone Recording</span>
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={stopRecording}
                    className="px-5 py-2.5 bg-slate-800 hover:bg-slate-900 text-white text-xs font-bold rounded-full shadow-md flex items-center space-x-2 animate-bounce"
                  >
                    <Square className="w-4 h-4 fill-current text-red-500" />
                    <span>Stop Recording ({formatSeconds(recordingSeconds)})</span>
                  </button>
                )}
              </div>

              {isRecording && (
                <div className="flex items-center justify-center space-x-1.5 pt-2">
                  <span className="w-2.5 h-2.5 bg-red-600 rounded-full animate-ping" />
                  <span className="text-xs font-mono text-red-700 font-bold">
                    Recording Live Call Audio: {formatSeconds(recordingSeconds)}
                  </span>
                </div>
              )}

              {recordError && (
                <div className="text-xs text-red-600 flex items-center justify-center space-x-1">
                  <AlertCircle className="w-3.5 h-3.5" />
                  <span>{recordError}</span>
                </div>
              )}

              {recordedUrl && !isRecording && (
                <div className="pt-2 flex flex-col items-center space-y-2">
                  <span className="text-xs font-bold text-emerald-700 flex items-center space-x-1">
                    <Check className="w-3.5 h-3.5" />
                    <span>Recorded ({formatSeconds(recordingSeconds)}) - Ready to analyze</span>
                  </span>
                  <audio controls src={recordedUrl} className="h-8 max-w-sm" />
                </div>
              )}
            </div>

            {/* Live speech preview if available */}
            <div>
              <label className="block text-[11px] font-bold text-slate-700 mb-1">
                Live Speech Transcript / Context Notes:
              </label>
              <textarea
                rows={2}
                value={liveTranscript || transcriptNotes}
                onChange={(e) => setTranscriptNotes(e.target.value)}
                placeholder="Spoken words and voice dialogue will transcribe here..."
                className="w-full p-2.5 text-xs border border-slate-300 rounded-lg outline-none focus:ring-1 focus:ring-navy-900 font-mono"
              />
            </div>
          </div>
        )}

        {/* Action Button */}
        <div className="flex items-center justify-end space-x-3 pt-2">
          <button
            type="submit"
            disabled={importing || (activeMode === 'upload' && !selectedFile) || (activeMode === 'record' && (!recordedBlob || isRecording))}
            className="px-5 py-2.5 bg-gradient-to-r from-blue-700 to-navy-900 hover:from-blue-800 hover:to-navy-950 text-white text-xs font-bold rounded-lg shadow-sm flex items-center space-x-2 transition-all disabled:opacity-50"
          >
            <Sparkles className="w-3.5 h-3.5 text-blue-300" />
            <span>{importing ? 'Processing & Analyzing Audio...' : 'Analyze Audio & Extract Key Points'}</span>
          </button>
        </div>
      </form>
    </div>
  );
}
