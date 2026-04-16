'use client';

import { useState } from 'react';
import { useAuth } from '@/lib/hooks/useAuth';
import RagQuery from '@/app/components/RagQuery';
import BotResponseTester from '@/app/components/BotResponseTester';

export default function RagPage() {
  const { user, isLoading } = useAuth();
  const [activeTab, setActiveTab] = useState<'query' | 'bot-test'>('query');

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Authentication Required</h1>
          <p className="text-gray-600">Please log in to access the RAG Query System</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">AI Assistant</h1>
          <p className="mt-2 text-gray-600">
            Powered by RAG (Retrieval-Augmented Generation) - Ask questions about your past meetings and test bot responses
          </p>
        </div>

        {/* Tabs */}
        <div className="bg-white shadow rounded-lg mb-6">
          <div className="border-b border-gray-200">
            <nav className="flex -mb-px">
              <button
                onClick={() => setActiveTab('query')}
                className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'query'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                📚 RAG Query
              </button>
              <button
                onClick={() => setActiveTab('bot-test')}
                className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'bot-test'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                🤖 Bot Response Tester
              </button>
            </nav>
          </div>

          <div className="p-6">
            {activeTab === 'query' && (
              <div>
                <p className="text-sm text-gray-600 mb-4">
                  Query your knowledge base with AI-powered context retrieval and response generation.
                </p>
              </div>
            )}
            {activeTab === 'bot-test' && (
              <div>
                <p className="text-sm text-gray-600 mb-4">
                  Test how the bot would respond to different trigger phrases without joining a live meeting.
                  Perfect for debugging bot name detection, filler injection, and response quality.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Tab Content */}
        {activeTab === 'query' && <RagQuery />}
        {activeTab === 'bot-test' && <BotResponseTester />}
      </div>
    </div>
  );
}
