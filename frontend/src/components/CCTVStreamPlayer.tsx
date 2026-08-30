import React, { useState, useEffect } from 'react';
import { Radio } from 'lucide-react';

interface CCTVStreamPlayerProps {
  cameraName: string;
  cameraId: string;
  intensity: 'low' | 'moderate' | 'high';
  observationsPerHour: number;
}

// Authentic Indian CCTV Stream Sources & Scenarios across 6 Metros
const CAMERA_FEEDS: Record<string, { image: string; roadType: string; activeClasses: string[] }> = {
  // BENGALURU
  'BLR-01': {
    image: 'https://images.unsplash.com/photo-1596176530529-78163a4f7af2?w=800&auto=format&fit=crop&q=80',
    roadType: 'Urban Arterial (MG Road Trinity)',
    activeClasses: ['AUTO-RICKSHAW 97%', 'MOTORCYCLE 98%', 'CAR 95%'],
  },
  'BLR-02': {
    image: 'https://images.unsplash.com/photo-1570125909232-eb263c188f7e?w=800&auto=format&fit=crop&q=80',
    roadType: 'Major Intersection (Brigade Rd)',
    activeClasses: ['BMTC BUS 99%', 'CAR 96%', 'MOTORCYCLE 94%'],
  },
  'BLR-03': {
    image: 'https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=800&auto=format&fit=crop&q=80',
    roadType: 'High-Density Choke (Silk Board Jct)',
    activeClasses: ['AUTO-RICKSHAW 98%', 'TWO-WHEELER 97%', 'BUS 99%'],
  },
  'BLR-04': {
    image: 'https://images.unsplash.com/photo-1545459720-aac8509eb02c?w=800&auto=format&fit=crop&q=80',
    roadType: 'Elevated Corridor (Hebbal Flyover)',
    activeClasses: ['SUV 98%', 'COMMERCIAL TRUCK 96%', 'CAR 97%'],
  },

  // DELHI NCR
  'DEL-01': {
    image: 'https://images.unsplash.com/photo-1587474260584-136574528ed5?w=800&auto=format&fit=crop&q=80',
    roadType: 'Ring Road Flyover (AIIMS)',
    activeClasses: ['SEDAN 99%', 'DTC BUS 98%', 'MOTORCYCLE 95%'],
  },
  'DEL-02': {
    image: 'https://images.unsplash.com/photo-1545459720-aac8509eb02c?w=800&auto=format&fit=crop&q=80',
    roadType: 'Expressway Toll (DND Flyway)',
    activeClasses: ['FASTAG CAR 99%', 'SUV 98%', 'VAN 94%'],
  },
  'DEL-03': {
    image: 'https://images.unsplash.com/photo-1506521781263-d8422e82f27a?w=800&auto=format&fit=crop&q=80',
    roadType: 'Commercial Expressway (Gurgaon Cyber City)',
    activeClasses: ['CAB 98%', 'CAR 97%', 'MOTORCYCLE 96%'],
  },

  // MUMBAI
  'BOM-01': {
    image: 'https://images.unsplash.com/photo-1588714477688-cf28a50e94f7?w=800&auto=format&fit=crop&q=80',
    roadType: 'Western Express Highway (Bandra)',
    activeClasses: ['HEAVY TRUCK 97%', 'AUTO-RICKSHAW 98%', 'CAR 96%'],
  },
  'BOM-02': {
    image: 'https://images.unsplash.com/photo-1545459720-aac8509eb02c?w=800&auto=format&fit=crop&q=80',
    roadType: 'Sea Link Expressway (Bandra-Worli)',
    activeClasses: ['SEDAN 99%', 'SUV 98%', 'CAR 97%'],
  },
  'BOM-03': {
    image: 'https://images.unsplash.com/photo-1596176530529-78163a4f7af2?w=800&auto=format&fit=crop&q=80',
    roadType: 'Marine Drive Coastal Arterial',
    activeClasses: ['TAXI 98%', 'CAR 97%', 'TWO-WHEELER 95%'],
  },

  // HYDERABAD
  'HYD-01': {
    image: 'https://images.unsplash.com/photo-1570125909232-eb263c188f7e?w=800&auto=format&fit=crop&q=80',
    roadType: 'IT Corridor (HITEC Cyber Towers)',
    activeClasses: ['AUTO-RICKSHAW 96%', 'CAR 98%', 'TSRTC BUS 99%'],
  },
  'HYD-02': {
    image: 'https://images.unsplash.com/photo-1545459720-aac8509eb02c?w=800&auto=format&fit=crop&q=80',
    roadType: 'Financial District (Gachibowli ORR)',
    activeClasses: ['CAR 99%', 'SUV 97%', 'MOTORCYCLE 96%'],
  },

  // CHENNAI
  'MAA-01': {
    image: 'https://images.unsplash.com/photo-1596176530529-78163a4f7af2?w=800&auto=format&fit=crop&q=80',
    roadType: 'Historic Arterial (Anna Salai)',
    activeClasses: ['MTC BUS 99%', 'MOTORCYCLE 98%', 'AUTO 96%'],
  },
  'MAA-02': {
    image: 'https://images.unsplash.com/photo-1545459720-aac8509eb02c?w=800&auto=format&fit=crop&q=80',
    roadType: 'IT Highway (OMR Tidel Park)',
    activeClasses: ['CAR 98%', 'BUS 99%', 'MOTORCYCLE 97%'],
  },

  // KOLKATA
  'CCU-01': {
    image: 'https://images.unsplash.com/photo-1588714477688-cf28a50e94f7?w=800&auto=format&fit=crop&q=80',
    roadType: 'Eastern Bypass (Science City)',
    activeClasses: ['YELLOW TAXI 99%', 'CAR 96%', 'BUS 98%'],
  },
  'CCU-02': {
    image: 'https://images.unsplash.com/photo-1570125909232-eb263c188f7e?w=800&auto=format&fit=crop&q=80',
    roadType: 'Historic Corridor (Howrah Bridge Approach)',
    activeClasses: ['WBSTC BUS 99%', 'AMBASSADOR TAXI 98%', 'MINIVAN 95%'],
  },
};

const DEFAULT_FEED = {
  image: 'https://images.unsplash.com/photo-1596176530529-78163a4f7af2?w=800&auto=format&fit=crop&q=80',
  roadType: 'Indian Metropolitan Surveillance Network',
  activeClasses: ['AUTO-RICKSHAW 96%', 'CAR 97%', 'MOTORCYCLE 95%'],
};

export const CCTVStreamPlayer: React.FC<CCTVStreamPlayerProps> = ({
  cameraName,
  cameraId,
  intensity,
  observationsPerHour,
}) => {
  const [timestamp, setTimestamp] = useState(new Date());
  const [bitrate, setBitrate] = useState(4180);

  useEffect(() => {
    const timer = setInterval(() => {
      setTimestamp(new Date());
      setBitrate(4000 + Math.floor(Math.random() * 350));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const feedKey = Object.keys(CAMERA_FEEDS).find(
    (k) => cameraName.toUpperCase().includes(k) || cameraId.toUpperCase().includes(k)
  ) || 'default';
  const feed = CAMERA_FEEDS[feedKey] || DEFAULT_FEED;

  return (
    <div className="relative rounded overflow-hidden border border-[#292932] aspect-video bg-[#050508] group select-none shadow-lg">
      {/* CCTV Camera Background Frame */}
      <img
        src={feed.image}
        alt={`Live Indian CCTV feed for ${cameraName}`}
        className="w-full h-full object-cover filter contrast-[1.15] brightness-90 saturate-[0.85]"
      />

      {/* CCTV Scanning Scanline Effect */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%)] bg-[length:100%_4px] pointer-events-none opacity-30" />

      {/* Simulated AI Object Detection Bounding Boxes Overlay */}
      <div className="absolute inset-0 pointer-events-none p-3">
        {/* Detection Box 1: Primary Vehicle */}
        <div className="absolute top-[28%] left-[18%] w-[34%] h-[44%] border-2 border-emerald-400/80 rounded-sm bg-emerald-500/10 transition-all duration-700">
          <div className="absolute -top-5 left-0 px-1 py-0.2 bg-emerald-500 text-[#0d0096] font-mono font-bold text-[9px] uppercase tracking-wider flex items-center gap-1 shadow">
            <span>{feed.activeClasses[0] || 'VEHICLE 97%'}</span>
          </div>
          <div className="absolute bottom-0 right-0 px-1 bg-[#0d0d15]/90 text-[8px] font-mono text-emerald-400">
            [ANPR OK]
          </div>
        </div>

        {/* Detection Box 2: Two-Wheeler / Bike */}
        <div className="absolute top-[38%] right-[16%] w-[22%] h-[36%] border border-[#38bdf8]/80 rounded-sm bg-[#38bdf8]/10 transition-all duration-700">
          <div className="absolute -top-4 left-0 px-1 py-0.2 bg-[#38bdf8] text-[#0d0d15] font-mono font-bold text-[8px] uppercase tracking-wider">
            <span>{feed.activeClasses[1] || 'MOTORCYCLE 98%'}</span>
          </div>
        </div>
      </div>

      {/* CCTV Top Left OSD (On-Screen Display) */}
      <div className="absolute top-2 left-2 flex flex-col gap-0.5 pointer-events-none">
        <div className="flex items-center gap-1.5 bg-[#0d0d15]/85 px-2 py-0.5 rounded border border-[#292932] font-mono text-[10px] text-emerald-400 backdrop-blur-sm">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
          <span className="font-bold tracking-wider">RTSP LIVE • CCTV-IN</span>
        </div>
        <div className="bg-[#0d0d15]/80 px-2 py-0.5 rounded text-[9px] font-mono text-[#e4e1ed]">
          CAM: <span className="font-bold text-[#c0c1ff]">{cameraName}</span>
        </div>
      </div>

      {/* CCTV Top Right OSD: Live IST Time & Telemetry */}
      <div className="absolute top-2 right-2 text-right bg-[#0d0d15]/85 px-2 py-1 rounded border border-[#292932] font-mono text-[9px] text-[#e4e1ed] backdrop-blur-sm pointer-events-none">
        <div className="text-emerald-400 font-bold">
          {timestamp.toISOString().replace('T', ' ').substring(0, 19)} IST
        </div>
        <div className="text-[#908fa0] text-[8px]">
          {bitrate} kbps • 30.0 FPS • H.265
        </div>
      </div>

      {/* CCTV Bottom Left: Location & Corridor */}
      <div className="absolute bottom-2 left-2 bg-[#0d0d15]/85 px-2 py-0.5 rounded border border-[#292932] font-mono text-[9px] text-[#908fa0] backdrop-blur-sm pointer-events-none">
        LOC: <strong className="text-[#e4e1ed]">{feed.roadType}</strong>
      </div>

      {/* CCTV Bottom Right: AI Inference Engine Badge */}
      <div className="absolute bottom-2 right-2 flex items-center gap-1 bg-[#8083ff]/20 border border-[#8083ff]/40 px-1.5 py-0.5 rounded font-mono text-[8px] text-[#c0c1ff] backdrop-blur-sm pointer-events-none">
        <Radio className="w-2.5 h-2.5 text-[#8083ff] animate-pulse" />
        <span>YOLOv8-ANPR • Pan-India</span>
      </div>
    </div>
  );
};
