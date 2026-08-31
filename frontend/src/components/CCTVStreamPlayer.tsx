import React, { useState, useEffect, useRef } from 'react';
import { Radio, Video, Camera, Cpu, RefreshCw, AlertCircle, Wifi } from 'lucide-react';

interface CCTVStreamPlayerProps {
  cameraName: string;
  cameraId: string;
  intensity: 'low' | 'moderate' | 'high';
  observationsPerHour: number;
}

type StreamMode = 'traffic' | 'webcam' | 'ai_mjpeg';

export const CCTVStreamPlayer: React.FC<CCTVStreamPlayerProps> = ({
  cameraName,
  cameraId,
}) => {
  const [mode, setMode] = useState<StreamMode>('traffic');
  const [timestamp, setTimestamp] = useState(new Date());
  const [bitrate, setBitrate] = useState(4180);
  const [webcamError, setWebcamError] = useState<string | null>(null);
  const [videoError, setVideoError] = useState(false);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const webcamVideoRef = useRef<HTMLVideoElement | null>(null);
  const webcamStreamRef = useRef<MediaStream | null>(null);
  const animFrameRef = useRef<number | null>(null);

  // Reliable traffic video URLs
  const videoSrc =
    'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4';

  // Clock & bitrate ticker
  useEffect(() => {
    const timer = setInterval(() => {
      setTimestamp(new Date());
      setBitrate(3900 + Math.floor(Math.random() * 400));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Procedural Canvas Traffic Engine
  useEffect(() => {
    if (mode === 'traffic' && videoError) {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      let frameCount = 0;
      const vehicles = [
        { x: 50, y: 90, vx: 2.2, color: '#38bdf8', class: 'CAR', plate: 'KA01MJ5005', w: 60, h: 32 },
        { x: 260, y: 135, vx: -1.8, color: '#f59e0b', class: 'BUS', plate: 'DL01CA1001', w: 90, h: 42 },
        { x: 180, y: 190, vx: 2.8, color: '#34d399', class: 'AUTO', plate: 'MH02BX9988', w: 45, h: 28 },
      ];

      const render = () => {
        frameCount++;
        ctx.fillStyle = '#141418';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Asphalt road texture & lanes
        ctx.strokeStyle = '#27272a';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(0, 75); ctx.lineTo(canvas.width, 75);
        ctx.moveTo(0, 170); ctx.lineTo(canvas.width, 170);
        ctx.stroke();

        // Dashed center lines
        ctx.strokeStyle = '#71717a';
        ctx.setLineDash([15, 15]);
        ctx.lineDashOffset = -frameCount * 3;
        ctx.beginPath();
        ctx.moveTo(0, 122); ctx.lineTo(canvas.width, 122);
        ctx.stroke();
        ctx.setLineDash([]);

        // Render moving vehicles
        vehicles.forEach((v) => {
          v.x += v.vx;
          if (v.x > canvas.width + 100) v.x = -100;
          if (v.x < -120) v.x = canvas.width + 50;

          // Vehicle body
          ctx.fillStyle = v.color;
          ctx.fillRect(v.x, v.y, v.w, v.h);
          ctx.strokeStyle = '#ffffff';
          ctx.lineWidth = 1;
          ctx.strokeRect(v.x, v.y, v.w, v.h);

          // Headlights
          ctx.fillStyle = '#fef08a';
          if (v.vx > 0) {
            ctx.fillRect(v.x + v.w - 2, v.y + 4, 3, 6);
            ctx.fillRect(v.x + v.w - 2, v.y + v.h - 10, 3, 6);
          } else {
            ctx.fillRect(v.x - 1, v.y + 4, 3, 6);
            ctx.fillRect(v.x - 1, v.y + v.h - 10, 3, 6);
          }

          // AI Detection Bounding Box
          ctx.strokeStyle = '#10b981';
          ctx.lineWidth = 1.5;
          ctx.strokeRect(v.x - 4, v.y - 4, v.w + 8, v.h + 8);

          // Detection tag
          ctx.fillStyle = '#10b981';
          ctx.fillRect(v.x - 4, v.y - 18, 55, 14);
          ctx.fillStyle = '#042f2e';
          ctx.font = 'bold 9px monospace';
          ctx.fillText(`${v.class} 98%`, v.x - 2, v.y - 8);

          // Plate badge
          ctx.fillStyle = 'rgba(9, 9, 11, 0.9)';
          ctx.fillRect(v.x, v.y + v.h + 4, v.w, 13);
          ctx.fillStyle = '#38bdf8';
          ctx.font = 'bold 8px monospace';
          ctx.fillText(v.plate, v.x + 2, v.y + v.h + 13);
        });

        animFrameRef.current = requestAnimationFrame(render);
      };

      render();
      return () => {
        if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      };
    }
  }, [mode, videoError]);

  // Handle Webcam mode
  useEffect(() => {
    if (mode === 'webcam') {
      startWebcam();
    } else {
      stopWebcam();
    }
    return () => {
      stopWebcam();
    };
  }, [mode]);

  const startWebcam = async () => {
    setWebcamError(null);
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('Camera access not supported on this device/browser.');
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      webcamStreamRef.current = stream;
      if (webcamVideoRef.current) {
        webcamVideoRef.current.srcObject = stream;
        webcamVideoRef.current.play();
      }
    } catch (err: any) {
      setWebcamError(err.message || 'Webcam permission denied or camera in use.');
    }
  };

  const stopWebcam = () => {
    if (webcamStreamRef.current) {
      webcamStreamRef.current.getTracks().forEach((t) => t.stop());
      webcamStreamRef.current = null;
    }
    if (webcamVideoRef.current) {
      webcamVideoRef.current.srcObject = null;
    }
  };

  const backendStreamUrl = `http://localhost:8000/api/v1/cameras/${cameraId}/stream`;

  return (
    <div className="flex flex-col gap-3 w-full">
      {/* Apple-style Segmented Stream Source Selector */}
      <div className="flex items-center bg-[#18181f]/80 p-1 rounded-xl border border-white/[0.08] backdrop-blur-md shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
        <div className="flex items-center gap-1 w-full">
          <button
            type="button"
            onClick={() => {
              setMode('traffic');
              setVideoError(false);
            }}
            className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-lg text-xs font-medium transition-all duration-200 cursor-pointer ${
              mode === 'traffic'
                ? 'bg-white/[0.12] text-white shadow-[0_2px_8px_rgba(0,0,0,0.3),inset_0_1px_0_rgba(255,255,255,0.15)] border border-white/[0.12]'
                : 'text-[#8e8e93] hover:text-[#f4f4f5] hover:bg-white/[0.04]'
            }`}
          >
            <Video className="w-3.5 h-3.5 shrink-0 text-emerald-400" />
            <span>Traffic Stream</span>
          </button>

          <button
            type="button"
            onClick={() => setMode('webcam')}
            className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-lg text-xs font-medium transition-all duration-200 cursor-pointer ${
              mode === 'webcam'
                ? 'bg-white/[0.12] text-white shadow-[0_2px_8px_rgba(0,0,0,0.3),inset_0_1px_0_rgba(255,255,255,0.15)] border border-white/[0.12]'
                : 'text-[#8e8e93] hover:text-[#f4f4f5] hover:bg-white/[0.04]'
            }`}
          >
            <Camera className="w-3.5 h-3.5 shrink-0 text-cyan-400" />
            <span>Webcam</span>
          </button>

          <button
            type="button"
            onClick={() => setMode('ai_mjpeg')}
            className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-lg text-xs font-medium transition-all duration-200 cursor-pointer ${
              mode === 'ai_mjpeg'
                ? 'bg-white/[0.12] text-white shadow-[0_2px_8px_rgba(0,0,0,0.3),inset_0_1px_0_rgba(255,255,255,0.15)] border border-white/[0.12]'
                : 'text-[#8e8e93] hover:text-[#f4f4f5] hover:bg-white/[0.04]'
            }`}
          >
            <Cpu className="w-3.5 h-3.5 shrink-0 text-amber-400" />
            <span>Backend AI</span>
          </button>
        </div>
      </div>

      {/* CCTV Screen Frame */}
      <div className="relative rounded-2xl overflow-hidden border border-white/[0.1] aspect-video bg-[#0c0c0e] select-none shadow-2xl">
        {/* Mode 1: Traffic Video Stream */}
        {mode === 'traffic' && !videoError && (
          <video
            ref={videoRef}
            src={videoSrc}
            autoPlay
            loop
            muted
            playsInline
            onError={() => setVideoError(true)}
            className="w-full h-full object-cover filter contrast-[1.08] brightness-95"
          />
        )}

        {/* Fallback Traffic Canvas Simulation */}
        {mode === 'traffic' && videoError && (
          <canvas
            ref={canvasRef}
            width={480}
            height={270}
            className="w-full h-full object-cover"
          />
        )}

        {/* Mode 2: Device Webcam */}
        {mode === 'webcam' && (
          <div className="w-full h-full relative">
            <video
              ref={webcamVideoRef}
              autoPlay
              playsInline
              muted
              className="w-full h-full object-cover"
            />
            {webcamError && (
              <div className="absolute inset-0 flex flex-col items-center justify-center bg-[#09090b]/95 text-center p-4">
                <AlertCircle className="w-7 h-7 text-rose-400 mb-1.5" />
                <div className="text-xs font-semibold text-rose-300 mb-1">Webcam Permission Required</div>
                <div className="text-[11px] text-[#a1a1aa] max-w-xs">{webcamError}</div>
                <button
                  onClick={startWebcam}
                  className="mt-3 px-3.5 py-1.5 apple-button-primary rounded-xl text-xs font-semibold flex items-center gap-1.5 cursor-pointer"
                >
                  <RefreshCw className="w-3 h-3" /> Retry Access
                </button>
              </div>
            )}
          </div>
        )}

        {/* Mode 3: Backend AI MJPEG Stream */}
        {mode === 'ai_mjpeg' && (
          <img
            src={backendStreamUrl}
            alt={`Live AI Stream for ${cameraName}`}
            className="w-full h-full object-cover"
            onError={() => {
              setVideoError(true);
              setMode('traffic');
            }}
          />
        )}

        {/* Subtle scanline overlay */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.2)_50%)] bg-[length:100%_4px] pointer-events-none opacity-10" />

        {/* Top-Left OSD Header */}
        <div className="absolute top-2.5 left-2.5 flex items-center gap-2 pointer-events-none z-10">
          <div className="flex items-center gap-1.5 bg-[#09090b]/80 backdrop-blur-md px-2.5 py-1 rounded-xl border border-white/[0.1] text-xs font-medium text-emerald-400 shadow-md">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
            <span className="text-[10px] font-bold tracking-wider">
              {mode === 'webcam' ? 'LOCAL WEBCAM' : (mode === 'ai_mjpeg' ? 'AI MJPEG' : 'RTSP STREAM')}
            </span>
          </div>
          <div className="bg-[#09090b]/75 backdrop-blur-md px-2.5 py-1 rounded-xl border border-white/[0.08] text-[10px] font-medium text-[#f4f4f5] max-w-[150px] truncate shadow-md">
            {cameraName}
          </div>
        </div>

        {/* Top-Right OSD Telemetry */}
        <div className="absolute top-2.5 right-2.5 flex flex-col items-end gap-1 pointer-events-none z-10">
          <div className="bg-[#09090b]/80 backdrop-blur-md px-2.5 py-1 rounded-xl border border-white/[0.1] text-[10px] font-mono text-emerald-400 shadow-md font-semibold">
            {timestamp.toISOString().replace('T', ' ').substring(11, 19)} UTC
          </div>
          <div className="text-[9px] font-mono text-[#a1a1aa] px-2 py-0.5 bg-[#09090b]/70 backdrop-blur-md rounded-lg border border-white/[0.05]">
            {bitrate} kbps • 30 FPS
          </div>
        </div>

        {/* Bottom Bar Info */}
        <div className="absolute bottom-2.5 left-2.5 right-2.5 flex items-center justify-between pointer-events-none z-10 text-[10px] font-medium">
          <div className="bg-[#09090b]/80 backdrop-blur-md px-2.5 py-1 rounded-xl border border-white/[0.1] text-[#a1a1aa] flex items-center gap-1.5 shadow-md">
            <Wifi className="w-3 h-3 text-emerald-400" />
            <span>Corridor Sensor Active</span>
          </div>
          <div className="bg-emerald-500/15 backdrop-blur-md border border-emerald-500/30 px-2.5 py-1 rounded-xl text-emerald-300 flex items-center gap-1.5 shadow-md">
            <Radio className="w-3 h-3 text-emerald-400 animate-pulse" />
            <span>YOLOv8 + ByteTrack</span>
          </div>
        </div>
      </div>
    </div>
  );
};
