/**
 * Digital Twin Logo Component
 * 
 * Displays the Digital Twin logo image with customizable size and shadow.
 * 
 * @param size - Logo size in pixels (default: 64)
 * @param showShadow - Whether to show drop shadow (default: false)
 */

import Image from 'next/image';

interface DigitalTwinLogoProps {
  size?: number;
  showShadow?: boolean;
}

export default function DigitalTwinLogo({ size = 64, showShadow = false }: DigitalTwinLogoProps) {
  return (
    <div 
      className="inline-flex items-center justify-center relative" 
      style={{ 
        width: `${size}px`, 
        height: `${size}px`,
        filter: showShadow ? 'drop-shadow(0 2px 8px rgba(217, 119, 87, 0.2))' : 'none'
      }}
    >
      <Image
        src="/logo.png"
        alt="Digital Twin Logo"
        width={size}
        height={size}
        className="object-contain"
        priority
      />
    </div>
  );
}
