import React from 'react';
import { parseSummary, cleanSummaryText, FormattedSummarySection } from '@/lib/utils/formatSummary';

interface FormattedSummaryDisplayProps {
  summaryText: string;
  className?: string;
}

export const FormattedSummaryDisplay: React.FC<FormattedSummaryDisplayProps> = ({ 
  summaryText, 
  className = '' 
}) => {
  // Clean and parse the summary
  const cleanedText = cleanSummaryText(summaryText);
  const sections = parseSummary(cleanedText);

  return (
    <div className={`space-y-4 ${className}`}>
      {sections.map((section, index) => (
        <div key={index}>
          {section.type === 'attendees' && (
            <div className="mb-4">
              <h4 className="text-base font-bold mb-2" style={{ color: 'var(--text-primary)' }}>
                {section.label}
              </h4>
              <p className="text-sm leading-relaxed" style={{ color: 'var(--text-primary)' }}>
                {section.content}
              </p>
            </div>
          )}
          
          {section.type === 'key_points' && (
            <div>
              <h4 className="text-base font-bold mb-3" style={{ color: 'var(--text-primary)' }}>
                {section.label}
              </h4>
              <div className="space-y-2">
                {section.content.split('\n').map((point, pointIndex) => (
                  point.trim() && (
                    <div key={pointIndex} className="flex items-start gap-2">
                      <span className="text-secondary mt-1 flex-shrink-0">•</span>
                      <p className="text-sm leading-relaxed flex-1" style={{ color: 'var(--text-primary)' }}>
                        {point.replace(/^[•\-]\s*/, '')}
                      </p>
                    </div>
                  )
                ))}
              </div>
            </div>
          )}
          
          {section.type === 'text' && (
            <p className="text-sm leading-relaxed whitespace-pre-wrap" style={{ color: 'var(--text-primary)' }}>
              {section.content}
            </p>
          )}
        </div>
      ))}
    </div>
  );
};
