import { useState, useRef, useEffect, useCallback } from 'react';
import {
  Settings,
  Link as LinkIcon,
  XCircle,
  ClipboardPaste,
  Play,
  Scissors,
  Clock,
  Check,
  Music,
  ChevronDown,
  ChevronUp,
  ArrowRight,
  Download,
  Folder,
  Image as ImageIcon,
  Info,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Terminal,
} from 'lucide-react';

const API = 'http://localhost:8000';

function friendlyError(e, launcherOnline) {
  if (!e) return 'Something went wrong.';
  const msg = e.message || String(e);
  if (msg === 'Failed to fetch' || msg.includes('NetworkError') || msg.includes('ERR_CONNECTION_REFUSED')) {
    if (launcherOnline || (window.electron && window.electron.isElectron)) {
      return 'Backend offline. Click "Start Server" above to launch.';
    }
    return 'Backend offline. Run start-launcher.bat to enable.';
  }
  return msg;
}

const QUALITY_OPTIONS = [
  { id: '4k', label: '4K', fps: '60fps', tag: 'UHD', audio: false },
  { id: '1080p60', label: '1080p', fps: '60fps', tag: 'FHD', audio: false },
  { id: '1080p30', label: '1080p', fps: '30fps', tag: 'FHD', audio: false },
  { id: '720p', label: '720p', fps: '30fps', tag: 'HD', audio: false },
  { id: 'audio', label: 'Audio', fps: 'Only', tag: null, audio: true },
];

function hhmmssToSeconds(t) {
  const parts = t.split(':').map(Number);
  if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
  if (parts.length === 2) return parts[0] * 60 + parts[1];
  return parts[0] || 0;
}

function secondsToHhmmss(s) {
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
}

export default function App() {
  const [url, setUrl] = useState('');
  const [downloadType, setDownloadType] = useState('full');
  const [quality, setQuality] = useState('1080p30');
  const [startTime, setStartTime] = useState('00:00:00');
  const [endTime, setEndTime] = useState('00:00:00');
  const [videoData, setVideoData] = useState(null);
  const [isFetching, setIsFetching] = useState(false);
  const [fetchError, setFetchError] = useState('');
  const [saveDir, setSaveDir] = useState('');
  const [downloadState, setDownloadState] = useState('idle');
  const [downloadLog, setDownloadLog] = useState([]);
  const [downloadProgress, setDownloadProgress] = useState(0);
  const [backendOnline, setBackendOnline] = useState(null);
  const [launcherOnline, setLauncherOnline] = useState(null);
  const [isStartingBackend, setIsStartingBackend] = useState(false);
  const abortRef = useRef(null);
  const isDownloadingRef = useRef(false);
  const downloadStateRef = useRef('idle');

  const [showSettings, setShowSettings] = useState(false);
  const [selectedBrowser, setSelectedBrowser] = useState(() => localStorage.getItem('selected_browser') || 'none');
  const [customUserAgent, setCustomUserAgent] = useState(() => localStorage.getItem('custom_user_agent') || '');
  const [concurrentDownloads, setConcurrentDownloads] = useState(() => {
    const saved = localStorage.getItem('concurrent_downloads');
    return saved ? parseInt(saved, 10) : 8;
  });

  const updateSelectedBrowser = (b) => {
    setSelectedBrowser(b);
    localStorage.setItem('selected_browser', b);
  };
  const updateCustomUserAgent = (ua) => {
    setCustomUserAgent(ua);
    localStorage.setItem('custom_user_agent', ua);
  };
  const updateConcurrentDownloads = (n) => {
    setConcurrentDownloads(n);
    localStorage.setItem('concurrent_downloads', String(n));
  };

  const setDownloadStateSync = (state) => {
    downloadStateRef.current = state;
    setDownloadState(state);
  };

  useEffect(() => {
    const check = async () => {
      try {
        const r = await fetch(`${API}/health`, { signal: AbortSignal.timeout(1500) });
        setBackendOnline(r.ok);
      } catch {
        setBackendOnline(false);
      }

      try {
        const r = await fetch('http://localhost:9999/health', { signal: AbortSignal.timeout(1500) });
        setLauncherOnline(r.ok);
      } catch {
        setLauncherOnline(false);
      }
    };
    check();
    const id = setInterval(check, 3000);
    return () => clearInterval(id);
  }, []);

  const handleStartBackend = useCallback(async () => {
    if (isStartingBackend) return;
    setIsStartingBackend(true);
    setFetchError('');
    try {
      if (window.electron && window.electron.isElectron) {
        await window.electron.startBackend();
        for (let i = 0; i < 10; i++) {
          await new Promise(r => setTimeout(r, 800));
          try {
            const r = await fetch(`${API}/health`, { signal: AbortSignal.timeout(800) });
            if (r.ok) {
              setBackendOnline(true);
              break;
            }
          } catch (_e) { void _e; }
        }
      } else if (launcherOnline) {
        const res = await fetch('http://localhost:9999/start', { method: 'POST' });
        if (res.ok) {
          for (let i = 0; i < 10; i++) {
            await new Promise(r => setTimeout(r, 800));
            try {
              const r = await fetch(`${API}/health`, { signal: AbortSignal.timeout(800) });
              if (r.ok) {
                setBackendOnline(true);
                break;
              }
            } catch (_e) { void _e; }
          }
        } else {
          setFetchError('Failed to trigger backend start via launcher.');
        }
      } else {
        setFetchError('Launcher offline. Please run start-launcher.bat first.');
      }
    } catch {
      setFetchError('Connection to launcher failed. Verify start-launcher.bat is active.');
    } finally {
      setIsStartingBackend(false);
    }
  }, [launcherOnline, isStartingBackend]);

  useEffect(() => {
    if ((launcherOnline || (window.electron && window.electron.isElectron)) && backendOnline === false && !isStartingBackend) {
      const timer = setTimeout(() => {
        handleStartBackend();
      }, 0);
      return () => clearTimeout(timer);
    }
  }, [launcherOnline, backendOnline, isStartingBackend, handleStartBackend]);

  const handlePaste = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text.trim()) {
        setUrl(text.trim());
        setVideoData(null);
        setFetchError('');
      }
    } catch {
      setFetchError('Clipboard access denied. Paste URL manually.');
    }
  };

  const handleClear = () => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    isDownloadingRef.current = false;
    setUrl('');
    setVideoData(null);
    setFetchError('');
    setDownloadStateSync('idle');
    setDownloadLog([]);
    setDownloadProgress(0);
  };

  const handleFetch = async () => {
    if (!url.trim()) return;
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    isDownloadingRef.current = false;
    setIsFetching(true);
    setVideoData(null);
    setFetchError('');
    setDownloadStateSync('idle');
    setDownloadLog([]);
    setDownloadProgress(0);
    try {
      const res = await fetch(`${API}/api/info`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: url.trim(),
          browser: selectedBrowser,
          user_agent: customUserAgent,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to fetch video info');
      }
      const data = await res.json();
      setVideoData(data);
      if (data.duration) {
        setEndTime(data.duration);
      }
    } catch (e) {
      setFetchError(friendlyError(e, launcherOnline));
    } finally {
      setIsFetching(false);
    }
  };

  const handleSelectFolder = async () => {
    try {
      const res = await fetch(`${API}/api/select-folder`, { method: 'POST' });
      const data = await res.json();
      if (data.path) setSaveDir(data.path);
    } catch {
      setFetchError(friendlyError(new Error('Failed to fetch'), launcherOnline));
    }
  };

  const handleDownload = async () => {
    if (!videoData || isDownloadingRef.current) return;

    isDownloadingRef.current = true;
    setDownloadStateSync('downloading');
    setDownloadLog([]);
    setDownloadProgress(0);
    setFetchError('');

    const effectiveSaveDir = saveDir || '';
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const res = await fetch(`${API}/api/download`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: url.trim(),
          quality,
          download_type: downloadType,
          start_time: startTime,
          end_time: endTime,
          save_dir: effectiveSaveDir,
          browser: selectedBrowser,
          user_agent: customUserAgent,
          concurrent_downloads: concurrentDownloads,
        }),
        signal: controller.signal,
      });

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let encounteredError = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const payload = JSON.parse(line.slice(6));
            if (payload.log) {
              setDownloadLog((prev) => [...prev.slice(-100), payload.log]);
              const match = payload.log.match(/(\d+\.?\d*)%/);
              if (match) setDownloadProgress(parseFloat(match[1]));
            }
            if (payload.status === 'done') {
              encounteredError = false;
              setDownloadStateSync('done');
            }
            if (payload.status === 'error') {
              encounteredError = true;
              setFetchError(payload.detail || 'Download failed');
              setDownloadStateSync('error');
            }
          } catch (_e) { void _e; }
        }
      }

      if (!encounteredError && downloadStateRef.current !== 'done' && downloadStateRef.current !== 'error') {
        setDownloadStateSync('done');
      }
    } catch (e) {
      if (e.name !== 'AbortError') {
        setFetchError(e.message || 'Download failed');
        setDownloadStateSync('error');
      } else {
        setDownloadStateSync('idle');
      }
    } finally {
      isDownloadingRef.current = false;
      abortRef.current = null;
    }
  };

  const adjustTime = (setter, current, delta) => {
    const secs = Math.max(0, hhmmssToSeconds(current) + delta);
    setter(secondsToHhmmss(secs));
  };

  const downloadButtonLabel = {
    idle: 'Download Video',
    downloading: 'Processing...',
    done: 'Download Success',
    error: 'Retry Download',
  }[downloadState];

  const downloadButtonClass = {
    idle: videoData
      ? 'bg-blue-600 hover:bg-blue-500 text-white hover:scale-[1.01] active:scale-[0.99]'
      : 'bg-zinc-900 text-zinc-500 cursor-not-allowed',
    downloading: 'bg-zinc-800 text-zinc-400 cursor-wait animate-pulse',
    done: 'bg-emerald-600 hover:bg-emerald-500 text-white hover:scale-[1.01] active:scale-[0.99]',
    error: 'bg-rose-600 hover:bg-rose-500 text-white hover:scale-[1.01] active:scale-[0.99]',
  }[downloadState];

  return (
    <div className="w-full min-h-screen dashboard-locked bg-[#09090b] flex flex-col font-sans text-zinc-100 relative select-none">

      <header className="flex items-center justify-between px-6 py-4 border-b border-zinc-800/50 bg-zinc-950/40 shrink-0 z-10">
        <div className="flex flex-col">
          <h1 className="font-display text-[15px] font-bold tracking-tight text-white leading-none">Fast Video Downloader</h1>
          <span className="text-[10px] text-zinc-500 font-medium mt-1">High-performance media extractor</span>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-zinc-900/60 border border-zinc-800/50 rounded-full px-3 py-1">
            <span className="text-[10px] font-semibold tracking-wide uppercase text-zinc-400 font-display">Engine Status</span>

            {backendOnline === null ? (
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-zinc-600 animate-pulse" />
                <span className="text-[11px] text-zinc-400 font-medium font-display">Initializing</span>
              </div>
            ) : backendOnline ? (
              <div className="flex items-center gap-1.5">
                <span className="w-2 rounded-full bg-emerald-500 aspect-square" />
                <span className="text-[11px] text-emerald-400 font-medium font-display">Online</span>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping shrink-0" />
                <span className="text-[11px] text-rose-400 font-medium font-display">Offline</span>

                <button
                  onClick={handleStartBackend}
                  disabled={isStartingBackend}
                  className="flex items-center gap-1 text-[10px] font-bold text-indigo-400 hover:text-white bg-indigo-500/10 hover:bg-indigo-600/20 border border-indigo-500/20 px-2 py-0.5 rounded-full transition-all active-press"
                >
                  {isStartingBackend ? (
                    <Loader2 size={10} className="animate-spin" />
                  ) : (
                    <Terminal size={10} />
                  )}
                  {isStartingBackend ? 'Starting...' : 'Start Server'}
                </button>
              </div>
            )}
          </div>
          <button
            onClick={() => setShowSettings(true)}
            className="p-1.5 rounded-lg bg-zinc-900/50 hover:bg-zinc-800/60 border border-zinc-800/40 hover:text-white transition-all text-zinc-400 active-press"
          >
            <Settings size={14} />
          </button>
        </div>
      </header>

      <main className="dashboard-main flex flex-col px-6 pt-5 pb-6 gap-5 overflow-y-auto z-10">

        <section className="flex flex-col gap-1.5 shrink-0">
          <label className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider font-display">Target Media URL</label>
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5">
            <div className={`flex-1 flex items-center glass-input rounded-xl px-4 gap-3 h-11 transition-all ${fetchError ? 'border-rose-500/50 bg-rose-950/5' : 'border-zinc-800/50'}`}>
              <LinkIcon size={14} className="text-zinc-500 shrink-0" />
              <input
                type="text"
                value={url}
                onChange={(e) => { setUrl(e.target.value); setFetchError(''); }}
                onKeyDown={(e) => e.key === 'Enter' && handleFetch()}
                placeholder="Paste video or audio link here (e.g. YouTube, Vimeo, Twitter)..."
                className="flex-1 bg-transparent text-[13px] text-zinc-200 placeholder-zinc-650 outline-none w-full min-w-0"
              />
              {fetchError && (
                <span className="flex items-center gap-1 text-rose-400 text-[11px] shrink-0 font-medium whitespace-nowrap bg-rose-500/10 border border-rose-500/20 px-2 py-0.5 rounded-md max-w-[150px] xs:max-w-[220px] sm:max-w-none truncate">
                  <AlertCircle size={11} className="shrink-0" />
                  <span className="truncate">{fetchError}</span>
                </span>
              )}
              {url && !fetchError && (
                <button onClick={handleClear} className="text-zinc-500 hover:text-zinc-300 transition-colors shrink-0 active-press">
                  <XCircle size={15} />
                </button>
              )}
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={handlePaste}
                className="flex-1 sm:flex-none flex items-center justify-center gap-1.5 h-11 bg-zinc-900/60 hover:bg-zinc-800/60 text-zinc-300 hover:text-white text-[12px] font-semibold px-4 rounded-xl border border-zinc-800/50 transition-all active-press"
              >
                <ClipboardPaste size={13} />
                Paste Link
              </button>

              <button
                onClick={handleFetch}
                disabled={!url.trim() || isFetching}
                className={`flex-1 sm:flex-none flex items-center justify-center gap-1.5 h-11 text-[12px] font-bold px-5 rounded-xl transition-all active-press shrink-0 ${url.trim() && !isFetching
                    ? 'bg-blue-600 hover:bg-blue-500 text-white'
                    : 'bg-zinc-900/40 text-zinc-500 border border-zinc-900/10 cursor-not-allowed'
                  }`}
              >
                {isFetching ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
                {isFetching ? 'Fetching...' : 'Analyze'}
              </button>
            </div>
          </div>
        </section>

        <section className="dashboard-grid grid grid-cols-1 md:grid-cols-2 gap-6 pb-5">

          <div className="dashboard-panel bg-[#121214]/50 border border-zinc-800/60 rounded-2xl flex flex-col p-6 min-w-0 justify-start h-auto gap-6 overflow-y-auto">

            <div className="flex flex-col gap-6">
              <div>
                <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest font-display block mb-2.5">Downloader Option</span>
                <div className="flex p-0.5 rounded-xl bg-zinc-950/80 border border-zinc-800/50">
                  <button
                    onClick={() => setDownloadType('full')}
                    className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-[12px] font-bold transition-all active-press ${downloadType === 'full'
                        ? 'bg-zinc-800 text-white'
                        : 'bg-transparent text-zinc-500 hover:text-zinc-300'
                      }`}
                  >
                    <Play size={12} className={downloadType === 'full' ? 'text-indigo-400' : 'text-zinc-600'} />
                    Entire Media
                  </button>
                  <button
                    onClick={() => setDownloadType('custom')}
                    className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-[12px] font-bold transition-all active-press ${downloadType === 'custom'
                        ? 'bg-zinc-800 text-white'
                        : 'bg-transparent text-zinc-500 hover:text-zinc-300'
                      }`}
                  >
                    <Scissors size={12} className={downloadType === 'custom' ? 'text-indigo-400' : 'text-zinc-600'} />
                    Range Trimmer
                  </button>
                </div>
              </div>

              <div className={`transition-opacity duration-200 ${downloadType === 'full' ? 'opacity-25 pointer-events-none' : ''}`}>
                <div className="flex items-center gap-2 mb-2.5">
                  <Clock size={12} className={downloadType === 'custom' ? 'text-indigo-400' : 'text-zinc-600'} />
                  <span className={`text-[10px] font-bold font-display tracking-widest uppercase ${downloadType === 'custom' ? 'text-zinc-400' : 'text-zinc-500'}`}>
                    Custom Time Range
                  </span>
                </div>

                <div className="flex items-center gap-3">
                  <div className="flex-1 flex flex-col gap-1.5">
                    <span className="text-[9px] font-bold text-zinc-500">START POINT</span>
                    <div className="flex items-center bg-zinc-950/80 rounded-lg px-3 h-9 border border-zinc-800/50">
                      <input
                        type="text"
                        value={startTime}
                        onChange={(e) => setStartTime(e.target.value)}
                        readOnly={downloadType === 'full'}
                        className="flex-1 bg-transparent text-white text-[12px] outline-none font-mono tracking-wider"
                      />
                      <div className="flex flex-col gap-0.5 ml-1.5 shrink-0">
                        <button onClick={() => adjustTime(setStartTime, startTime, 1)} className="text-zinc-500 hover:text-indigo-400 transition-colors"><ChevronUp size={10} /></button>
                        <button onClick={() => adjustTime(setStartTime, startTime, -1)} className="text-zinc-500 hover:text-indigo-400 transition-colors"><ChevronDown size={10} /></button>
                      </div>
                    </div>
                  </div>

                  <ArrowRight size={14} className="text-zinc-700 shrink-0 mt-5" />

                  <div className="flex-1 flex flex-col gap-1.5">
                    <span className="text-[9px] font-bold text-zinc-500">END POINT</span>
                    <div className="flex items-center bg-zinc-950/80 rounded-lg px-3 h-9 border border-zinc-800/50">
                      <input
                        type="text"
                        value={endTime}
                        onChange={(e) => setEndTime(e.target.value)}
                        readOnly={downloadType === 'full'}
                        className="flex-1 bg-transparent text-white text-[12px] outline-none font-mono tracking-wider"
                      />
                      <div className="flex flex-col gap-0.5 ml-1.5 shrink-0">
                        <button onClick={() => adjustTime(setEndTime, endTime, 1)} className="text-zinc-500 hover:text-indigo-400 transition-colors"><ChevronUp size={10} /></button>
                        <button onClick={() => adjustTime(setEndTime, endTime, -1)} className="text-zinc-500 hover:text-indigo-400 transition-colors"><ChevronDown size={10} /></button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-auto pt-2">
              <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest font-display block mb-2.5">Export Quality</span>
              <div className="grid grid-cols-2 xs:grid-cols-3 sm:grid-cols-5 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-2">
                {QUALITY_OPTIONS.map((q) => {
                  const active = quality === q.id;
                  return (
                    <button
                      key={q.id}
                      onClick={() => setQuality(q.id)}
                      className={`relative flex flex-col items-center justify-center gap-1 rounded-xl border transition-all active-press h-[74px] px-1.5 ${active
                          ? 'border-indigo-500/40 bg-indigo-500/10 text-indigo-300'
                          : 'border-zinc-800/60 bg-zinc-900/30 text-zinc-400 hover:bg-zinc-800/30 hover:border-zinc-700/50'
                        }`}
                    >
                      {active && (
                        <span className="absolute top-1.5 right-1.5 w-3.5 h-3.5 bg-indigo-500 rounded-full flex items-center justify-center">
                          <Check size={8} className="text-white" strokeWidth={3.5} />
                        </span>
                      )}
                      <span className="text-[13px] font-bold font-display tracking-tight leading-none">
                        {q.label}
                      </span>
                      <span className="text-[9px] font-medium leading-none opacity-80">
                        {q.fps}
                      </span>
                      {q.tag ? (
                        <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded mt-1 leading-none ${active ? 'bg-indigo-950/60 text-indigo-300' : 'bg-zinc-800 text-zinc-400'}`}>
                          {q.tag}
                        </span>
                      ) : (
                        <Music size={10} className="mt-1.5" />
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

          </div>

          <div className="dashboard-panel bg-[#121214]/50 border border-zinc-800/60 rounded-2xl flex flex-col p-6 min-w-0 h-auto overflow-hidden">
            <div className="shrink-0 flex items-center justify-between mb-4">
              <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest font-display">Media Inspector</span>
            </div>

            <div className="dashboard-panel-scrollable flex-1 flex flex-col gap-4 min-h-0 overflow-y-auto">
              {isFetching ? (
                <div className="flex-1 flex flex-col items-center justify-center gap-3 bg-zinc-900/20 rounded-xl py-10">
                  <Loader2 size={24} className="text-indigo-500 animate-spin" />
                  <p className="text-[12px] text-zinc-400 font-medium">Extracting media container metadata...</p>
                </div>
              ) : !videoData ? (
                <div className="flex-1 flex flex-col items-center justify-center gap-3 border border-dashed border-zinc-800/60 rounded-xl py-12">
                  <div className="w-11 h-11 bg-zinc-900 rounded-full flex items-center justify-center border border-zinc-800/50">
                    <ImageIcon size={18} className="text-zinc-500" />
                  </div>
                  <div className="text-center px-4">
                    <p className="text-[12px] text-zinc-300 font-semibold font-display">Awaiting Media URL</p>
                    <p className="text-[10px] text-zinc-500 mt-1 max-w-[280px] mx-auto leading-relaxed">
                      Enter a supported link in the address bar above to analyze stream parameters and thumbnail.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col gap-4 flex-1 min-h-0">
                  <div className="flex flex-col sm:flex-row gap-4 shrink-0">
                    <div className="w-full sm:w-[40%] aspect-video rounded-xl overflow-hidden shrink-0 flex items-center justify-center relative bg-zinc-950 border border-zinc-800/50 group">
                      {videoData.thumbnail ? (
                        <img src={videoData.thumbnail} alt="Video thumbnail" className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105" />
                      ) : (
                        <ImageIcon size={22} className="text-zinc-650" />
                      )}
                      <div className="absolute inset-0 flex items-center justify-center bg-black/40 group-hover:bg-black/50 transition-colors">
                        <div className="w-9 h-9 bg-indigo-500 hover:bg-indigo-600 rounded-full flex items-center justify-center transition-transform active-press">
                          <Play size={13} className="text-white fill-white ml-0.5" />
                        </div>
                      </div>
                    </div>

                    <div className="flex-1 grid grid-cols-2 gap-x-4 gap-y-3 min-w-0">
                      {[
                        ['Title', videoData.title, 'text-zinc-200 font-bold col-span-2 text-[13px] line-clamp-2'],
                        ['Uploader', videoData.uploader, 'text-zinc-300 font-semibold text-[12px]'],
                        ['Duration', videoData.duration, 'text-zinc-400 font-mono text-[12px]'],
                        ['Resolution', videoData.formats?.[quality]?.resolution || 'Unknown', 'text-zinc-400 text-[12px]'],
                        ['Est. Size', videoData.formats?.[quality]?.size || 'N/A', 'text-zinc-300 font-medium text-[12px]'],
                        ['Codec', videoData.formats?.[quality]?.codec || 'Unknown', 'text-zinc-400 font-mono text-[10px]'],
                      ].map(([label, value, cls]) => (
                        <div key={label} className={`flex flex-col min-w-0 ${cls.includes('col-span-2') ? 'col-span-2' : ''}`}>
                          <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider leading-none mb-1">{label}</span>
                          <span className={`truncate ${cls}`}>{value}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {downloadState !== 'idle' && (
                    <div className="flex flex-col gap-2.5 flex-1 min-h-[180px] sm:min-h-0">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest font-display">
                          {downloadState === 'done' ? 'PROCESS FINISHED' : downloadState === 'error' ? 'PROCESS FAILED' : 'STREAM DOWNLOAD PROGRESS'}
                        </span>
                        <span className="text-[10px] font-semibold font-mono bg-zinc-900 rounded px-2 py-0.5">
                          {downloadState === 'downloading' ? `${downloadProgress.toFixed(1)}%` : ''}
                          {downloadState === 'done' && <span className="text-emerald-400 flex items-center gap-1"><CheckCircle2 size={10} /> Completed</span>}
                          {downloadState === 'error' && <span className="text-rose-400 flex items-center gap-1"><AlertCircle size={10} /> Failed</span>}
                        </span>
                      </div>

                      <div className="w-full h-1.5 bg-zinc-950 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-300 ${downloadState === 'done'
                              ? 'bg-emerald-500'
                              : downloadState === 'error'
                                ? 'bg-rose-500'
                                : 'bg-blue-600'
                            }`}
                          style={{ width: `${downloadState === 'done' ? 100 : downloadProgress}%` }}
                        />
                      </div>

                      <div className="flex-1 bg-zinc-950/60 border border-zinc-800/60 rounded-xl p-3 overflow-y-auto min-h-0 font-mono text-[10px] text-zinc-400 leading-normal shadow-inner relative">
                        {downloadLog.length === 0 && <span className="text-zinc-600 italic">Initializing downloader stream output...</span>}
                        {downloadLog.map((line, i) => {
                          let colorClass = 'text-zinc-400';
                          if (line.includes('[download]')) colorClass = 'text-indigo-400/90';
                          if (line.includes('ERROR') || line.includes('error')) colorClass = 'text-rose-400/90';
                          if (line.includes('[ffmpeg]') || line.includes('[Merger]')) colorClass = 'text-amber-400/85';
                          return (
                            <div key={i} className={`${colorClass} py-0.5 border-b border-zinc-900/30 break-all`}>
                              {line}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {downloadState === 'idle' && (
                    <div className="flex items-start gap-2.5 bg-zinc-900/30 rounded-xl p-3 shrink-0 mt-auto border border-zinc-800/40">
                      <Info size={13} className="text-indigo-400 mt-0.5 shrink-0" />
                      <p className="text-[10px] text-zinc-500 leading-relaxed">
                        Metadata extraction relies on yt-dlp. Stream file dimensions, bitrates, and estimated file sizes are approximates based on matching tracks.
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

        </section>
      </main>

      <footer className="flex flex-col sm:flex-row items-center justify-between gap-4 px-6 py-4 bg-zinc-950/90 border-t border-zinc-800/50 shrink-0 z-10">
        <div className="flex items-center justify-between sm:justify-start gap-3 w-full sm:w-auto">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-zinc-900/60 border border-zinc-800/50 flex items-center justify-center text-zinc-400">
              <Folder size={16} />
            </div>
            <div className="flex flex-col leading-none">
              <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider mb-1">Destination Target</span>
              <span className="text-[12px] font-semibold text-zinc-300 max-w-[160px] sm:max-w-xs truncate" title={saveDir || 'System Default Downloads'}>
                {saveDir || 'System Default Downloads'}
              </span>
            </div>
          </div>
          <button
            onClick={handleSelectFolder}
            className="ml-2 bg-zinc-900/60 hover:bg-zinc-800/60 border border-zinc-800/50 hover:border-zinc-700/40 text-[11px] text-zinc-300 hover:text-white px-3 py-1.5 rounded-lg transition-all active-press font-semibold"
          >
            Change
          </button>
        </div>

        <a
          href="https://www.instagram.com/nightlander_krishan/"
          target="_blank"
          rel="noopener noreferrer"
          className="hidden sm:block text-[10px] text-zinc-500 hover:text-indigo-400 transition-colors duration-200 tracking-wide font-medium"
        >
          Made by NioKrishan
        </a>

        <button
          disabled={!videoData || isFetching || downloadState === 'downloading'}
          onClick={handleDownload}
          className={`flex items-center justify-center gap-2 px-12 py-3 rounded-xl text-[13px] font-extrabold transition-all duration-200 w-full sm:w-auto ${downloadButtonClass}`}
        >
          {downloadState === 'downloading' ? (
            <Loader2 size={14} className="animate-spin" />
          ) : downloadState === 'done' ? (
            <CheckCircle2 size={14} />
          ) : (
            <Download size={14} />
          )}
          {downloadButtonLabel}
        </button>
      </footer>

      {showSettings && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-md animate-fade-in p-4">
          <div className="bg-[#121214]/95 border border-zinc-800/80 rounded-2xl w-full max-w-md shadow-2xl overflow-hidden animate-zoom-in flex flex-col max-h-[90vh]">

            <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800/50 bg-zinc-950/40">
              <div className="flex items-center gap-2">
                <Settings className="text-indigo-400 animate-spin-slow" size={16} />
                <h2 className="font-display text-[13px] font-bold text-white uppercase tracking-wider">Engine Settings</h2>
              </div>
              <button
                onClick={() => setShowSettings(false)}
                className="text-zinc-400 hover:text-white p-1 hover:bg-zinc-800/50 rounded-lg transition-colors active-press"
              >
                <XCircle size={16} />
              </button>
            </div>

            <div className="p-6 flex flex-col gap-6 overflow-y-auto">

              <div className="flex flex-col gap-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest font-display">Browser Cookies Sync</span>
                  <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 font-display">Age-Gate Bypass</span>
                </div>
                <p className="text-[10px] text-zinc-500 leading-normal">
                  Imports session cookies from your browser to authenticate downloads on restricted platforms (e.g. age gates, login walls, adult websites).
                </p>
                <div className="grid grid-cols-2 gap-2 mt-1">
                  {[
                    { id: 'none', label: 'None (Default)' },
                    { id: 'chrome', label: 'Chrome' },
                    { id: 'firefox', label: 'Firefox' },
                    { id: 'edge', label: 'Edge' },
                    { id: 'brave', label: 'Brave' },
                    { id: 'opera', label: 'Opera' },
                    { id: 'safari', label: 'Safari' },
                    { id: 'vivaldi', label: 'Vivaldi' },
                  ].map((browser) => {
                    const active = selectedBrowser === browser.id;
                    return (
                      <button
                        key={browser.id}
                        onClick={() => updateSelectedBrowser(browser.id)}
                        className={`flex items-center justify-between px-3 py-2 rounded-xl border transition-all active-press text-[11px] font-bold ${
                          active
                            ? 'border-indigo-500/40 bg-indigo-500/10 text-indigo-300'
                            : 'border-zinc-800/60 bg-zinc-900/20 text-zinc-405 hover:bg-zinc-800/30 hover:border-zinc-700/50 hover:text-zinc-300'
                        }`}
                      >
                        <span>{browser.label}</span>
                        {active && <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" />}
                      </button>
                    );
                  })}
                </div>
                {selectedBrowser !== 'none' && (
                  <div className="flex items-start gap-2 bg-amber-500/5 border border-amber-500/15 rounded-xl p-2.5 mt-1">
                    <AlertCircle size={12} className="text-amber-400 mt-0.5 shrink-0" />
                    <p className="text-[9px] text-amber-500/80 leading-normal">
                      Important: Ensure {selectedBrowser} is fully closed before initiating downloads if you see cookies database lock errors.
                    </p>
                  </div>
                )}
              </div>

              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest font-display">Download Speed (Threads)</span>
                  <span className="text-[10px] font-mono font-bold text-indigo-400">{concurrentDownloads} concurrent paths</span>
                </div>
                <p className="text-[10px] text-zinc-500 leading-normal">
                  Sets the number of parallel download streams. Higher values accelerate fragment downloads.
                </p>
                <div className="flex items-center gap-3 mt-1.5">
                  <input
                    type="range"
                    min="1"
                    max="16"
                    value={concurrentDownloads}
                    onChange={(e) => updateConcurrentDownloads(parseInt(e.target.value, 10))}
                    className="flex-1 accent-indigo-500 h-1 bg-zinc-800 rounded-lg cursor-pointer appearance-none"
                  />
                  <div className="w-8 text-center text-[11px] font-mono bg-zinc-950 border border-zinc-800 rounded py-0.5 font-bold text-zinc-300">
                    {concurrentDownloads}
                  </div>
                </div>
              </div>

              <div className="flex flex-col gap-2">
                <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest font-display">Custom Network Identity</span>
                <p className="text-[10px] text-zinc-500 leading-normal">
                  Specify a custom HTTP User-Agent string to bypass bot blockers. Leave empty to use system default.
                </p>
                <input
                  type="text"
                  value={customUserAgent}
                  onChange={(e) => updateCustomUserAgent(e.target.value)}
                  placeholder="Mozilla/5.0 (Windows NT 10.0; Win64; x64)..."
                  className="bg-zinc-950/80 rounded-xl px-3 py-2 text-[11px] outline-none font-mono text-zinc-300 border border-zinc-800/50 focus:border-indigo-500/40 w-full placeholder-zinc-700"
                />
              </div>

            </div>

            <div className="px-6 py-4 bg-zinc-950/60 border-t border-zinc-800/50 flex justify-end">
              <button
                onClick={() => setShowSettings(false)}
                className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-[12px] px-5 py-2 rounded-xl transition-all active-press"
              >
                Apply & Save Settings
              </button>
            </div>

          </div>
        </div>
      )}

    </div>
  );
}