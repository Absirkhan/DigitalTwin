"use client";

import React from 'react';

interface BotSpeakingWarningProps {
  variant?: 'default' | 'compact';
}

export default function BotSpeakingWarning({ variant = 'default' }: BotSpeakingWarningProps) {
  if (variant === 'compact') {
    return (
      <div className="bg-yellow-50 border-l-4 border-yellow-400 p-3 rounded">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-yellow-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <p className="text-sm text-yellow-700">
              <strong>Test before important meetings.</strong> Bot speaking is experimental.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded-lg">
      <div className="flex items-start">
        <div className="flex-shrink-0">
          <svg className="h-6 w-6 text-yellow-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        </div>
        <div className="ml-3">
          <h3 className="text-sm font-medium text-yellow-800">
            Important: Bot Speaking is Experimental
          </h3>
          <div className="mt-2 text-sm text-yellow-700">
            <ul className="list-disc pl-5 space-y-1">
              <li>
                <strong>Test thoroughly</strong> before using in important meetings
              </li>
              <li>
                Bot will only respond when <strong>directly addressed</strong> by name (e.g., "Hey BotName, ...")
              </li>
              <li>
                Do not enable for meetings similar to ones you have never tested with the bot
              </li>
              <li>
                Start with casual/internal meetings to verify behavior
              </li>
              <li>
                You can emergency disable during the meeting if needed
              </li>
            </ul>
          </div>
          <div className="mt-3 text-xs text-yellow-600 bg-yellow-100 p-2 rounded">
            <strong>Recommended workflow:</strong> Create a test meeting → Enable bot speaking → Join with a friend →
            Test by saying "Hey [BotName], what's the weather?" → Verify response quality → Then use in real meetings.
          </div>
        </div>
      </div>
    </div>
  );
}
