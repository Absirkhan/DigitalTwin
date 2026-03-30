'use client';

import { useAuth } from '@/lib/hooks/useAuth';
import RagQuery from '@/app/components/RagQuery';

export default function RagPage() {
  const { user, loading } = useAuth();

  if (loading) {
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
            Powered by RAG (Retrieval-Augmented Generation) - Ask questions about your past meetings and get intelligent, context-aware responses
          </p>
        </div>

        <RagQuery />
      </div>
    </div>
  );
}
