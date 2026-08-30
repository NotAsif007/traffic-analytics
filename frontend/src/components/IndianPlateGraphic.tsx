import React from 'react';

interface IndianPlateGraphicProps {
  plateNumber: string;
  isHsrp?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export const IndianPlateGraphic: React.FC<IndianPlateGraphicProps> = ({
  plateNumber,
  isHsrp = true,
  size = 'md',
}) => {
  const formatted = plateNumber.replace(/\s+/g, '').toUpperCase();
  const stateCode = formatted.slice(0, 2);
  const districtCode = formatted.slice(2, 4);
  const series = formatted.length > 8 ? formatted.slice(4, formatted.length - 4) : formatted.slice(4, 5);
  const uniqueNum = formatted.slice(formatted.length - 4);

  const displayPlate = `${stateCode} ${districtCode} ${series} ${uniqueNum}`.trim();

  const sizeClasses = {
    sm: 'px-2 py-1 text-xs',
    md: 'px-3 py-1.5 text-base',
    lg: 'px-5 py-2 text-2xl',
  }[size];

  return (
    <div className={`inline-flex items-center rounded-sm bg-[#ffffff] border-2 border-[#1a1a24] text-[#111111] font-mono font-bold shadow-md select-none tracking-wider ${sizeClasses}`}>
      {/* Left Blue HSRP Section */}
      {isHsrp && (
        <div className="flex flex-col items-center justify-center mr-2 pr-1.5 border-r border-[#333333]/30 leading-none">
          <div className="w-2 h-2 rounded-full border border-blue-600 flex items-center justify-center text-[6px] text-blue-700 font-sans font-bold">
            ☸
          </div>
          <span className="text-[7px] font-sans font-extrabold text-blue-800 tracking-tighter mt-0.5">
            IND
          </span>
        </div>
      )}

      {/* Embossed License Plate Text */}
      <span className="text-[#0a0a0a] drop-shadow-[0_1px_1px_rgba(0,0,0,0.3)]">
        {displayPlate || formatted}
      </span>
    </div>
  );
};
