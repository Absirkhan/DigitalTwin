/**
 * Utility functions for formatting AI-generated summaries
 */

export interface FormattedSummarySection {
  type: 'attendees' | 'key_points' | 'text';
  label?: string;
  content: string;
}

/**
 * Parse and format raw summary text into structured sections
 * Handles formats like:
 * - "Attendees: John Doe Key Points: - Item 1 - Item 2"
 * - "Attendees: John Doe, Jane Smith\nKey Points:\n- Discussion about X\n- Action items: Y"
 */
export function parseSummary(summaryText: string): FormattedSummarySection[] {
  if (!summaryText || summaryText.trim() === '') {
    return [];
  }

  const sections: FormattedSummarySection[] = [];
  
  // Normalize the text - replace multiple spaces with single space, but preserve intentional line breaks
  let normalizedText = summaryText.trim();
  
  // Pattern to match "Attendees:" followed by content until "Key Points:" or end
  const attendeesMatch = normalizedText.match(/Attendees:\s*([^]*?)(?=Key Points:|$)/i);
  
  // Pattern to match "Key Points:" followed by the rest
  const keyPointsMatch = normalizedText.match(/Key Points:\s*([^]*?)$/i);
  
  if (attendeesMatch && attendeesMatch[1]) {
    const attendeesContent = attendeesMatch[1].trim();
    sections.push({
      type: 'attendees',
      label: 'Attendees',
      content: attendeesContent
    });
  }
  
  if (keyPointsMatch && keyPointsMatch[1]) {
    const keyPointsContent = keyPointsMatch[1].trim();
    
    // Format key points - ensure bullet points are on separate lines
    const formattedKeyPoints = formatKeyPoints(keyPointsContent);
    
    sections.push({
      type: 'key_points',
      label: 'Key Points',
      content: formattedKeyPoints
    });
  }
  
  // If no structured format detected, return the whole text
  if (sections.length === 0) {
    sections.push({
      type: 'text',
      content: normalizedText
    });
  }
  
  return sections;
}

/**
 * Format key points to ensure proper bullet point structure
 */
function formatKeyPoints(text: string): string {
  // Split by dash that starts a line or follows whitespace
  const points = text
    .split(/\s*-\s*/)
    .map(point => point.trim())
    .filter(point => point.length > 0);
  
  if (points.length === 0) {
    return text;
  }
  
  // Rejoin with proper formatting and capitalize first letter of each point
  return points.map(point => {
    const capitalizedPoint = point.charAt(0).toUpperCase() + point.slice(1);
    return `• ${capitalizedPoint}`;
  }).join('\n');
}

/**
 * Capitalize the first letter of each sentence
 */
function capitalizeSentences(text: string): string {
  if (!text) return '';
  
  // Split by sentence-ending punctuation followed by space
  return text
    .replace(/(^|[.!?]\s+)([a-z])/g, (match, separator, letter) => {
      return separator + letter.toUpperCase();
    })
    // Capitalize the very first character if it's a letter
    .replace(/^[a-z]/, (match) => match.toUpperCase());
}

/**
 * Clean up common transcription/generation errors in summary text
 */
export function cleanSummaryText(text: string): string {
  if (!text) return '';
  
  let cleanedText = text
    // Fix common word errors
    .replace(/\bprint\b/gi, 'sprint')
    .replace(/\bPrint\b/g, 'Sprint')
    // Fix spacing around punctuation
    .replace(/\s+([.,;:!?])/g, '$1')
    .replace(/([.,;:!?])(?=[A-Za-z])/g, '$1 ')
    // Remove extra whitespace
    .replace(/\s+/g, ' ')
    .trim();
  
  // Capitalize first letter of each sentence
  cleanedText = capitalizeSentences(cleanedText);
  
  return cleanedText;
}
