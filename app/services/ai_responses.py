"""
AI response generation service using RAG
"""

import openai
from typing import List, Dict
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.llms import OpenAI
from langchain.chains import RetrievalQA
from langchain.document_loaders import TextLoader

from app.core.config import settings
from app.core.celery import celery_app

# Initialize OpenAI
openai.api_key = settings.OPENAI_API_KEY


class RAGResponseGenerator:
    def __init__(self, twin_id: int):
        self.twin_id = twin_id
        self.embeddings = OpenAIEmbeddings()
        self.llm = OpenAI(temperature=0.7)
        self.vectorstore = None
        self.qa_chain = None
        self.load_knowledge_base()
    
    def load_knowledge_base(self):
        """Load and index knowledge base for the digital twin"""
        try:
            # Load documents (meeting transcripts, user preferences, etc.)
            knowledge_path = f"{settings.VECTOR_DB_PATH}/twin_{self.twin_id}"
            
            # Initialize vector store
            self.vectorstore = Chroma(
                persist_directory=knowledge_path,
                embedding_function=self.embeddings
            )
            
            # Create QA chain
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=self.vectorstore.as_retriever(search_kwargs={"k": 3})
            )
            
        except Exception as e:
            print(f"Error loading knowledge base: {e}")
    
    def add_documents(self, documents: List[str]):
        """Add new documents to the knowledge base"""
        try:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=settings.CHUNK_SIZE,
                chunk_overlap=settings.CHUNK_OVERLAP
            )
            
            # Split documents into chunks
            chunks = []
            for doc in documents:
                doc_chunks = text_splitter.split_text(doc)
                chunks.extend(doc_chunks)
            
            # Add to vector store
            self.vectorstore.add_texts(chunks)
            self.vectorstore.persist()
            
        except Exception as e:
            print(f"Error adding documents: {e}")
    
    def generate_response(self, query: str, context: Dict = None) -> str:
        """Generate contextual response using RAG"""
        try:
            # Get twin personality and preferences
            personality_prompt = self.get_personality_prompt()
            
            # Enhance query with context
            enhanced_query = f"""
            Context: {context if context else 'General meeting discussion'}
            
            User Query: {query}
            
            Please respond as the digital twin with the following personality:
            {personality_prompt}
            
            Keep the response concise and professional.
            """
            
            # Generate response using RAG
            if self.qa_chain:
                response = self.qa_chain.run(enhanced_query)
            else:
                # Fallback to direct OpenAI call
                response = self.generate_fallback_response(enhanced_query)
            
            return response
            
        except Exception as e:
            print(f"Error generating response: {e}")
            return "I apologize, but I'm having trouble processing that request right now."
    
    def get_personality_prompt(self) -> str:
        """Get personality prompt for the digital twin"""
        # In a real implementation, this would be loaded from the database
        return """
        You are a professional digital assistant representing your user in meetings.
        You are knowledgeable, concise, and helpful.
        You speak in a professional but friendly tone.
        You can provide insights based on previous meetings and user preferences.
        """
    
    def generate_fallback_response(self, query: str) -> str:
        """Generate response using direct OpenAI call as fallback"""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.get_personality_prompt()},
                    {"role": "user", "content": query}
                ],
                max_tokens=150,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error with fallback response: {e}")
            return "I'm sorry, I'm unable to respond at the moment."


def generate_meeting_response(message: str, twin_id: int, context: Dict = None) -> str:
    """Generate response for meeting interaction"""
    generator = RAGResponseGenerator(twin_id)
    return generator.generate_response(message, context)


@celery_app.task
def process_meeting_transcript(meeting_id: int, transcript: str, twin_id: int):
    """Process meeting transcript and update knowledge base"""
    try:
        generator = RAGResponseGenerator(twin_id)
        
        # Add transcript to knowledge base
        generator.add_documents([transcript])
        
        # Generate meeting summary
        summary_query = f"Summarize the key points from this meeting transcript: {transcript}"
        summary = generator.generate_response(summary_query)
        
        # Extract action items
        action_query = f"Extract action items and next steps from this meeting transcript: {transcript}"
        action_items = generator.generate_response(action_query)
        
        return {
            'meeting_id': meeting_id,
            'summary': summary,
            'action_items': action_items,
            'status': 'completed'
        }
        
    except Exception as e:
        print(f"Error processing transcript: {e}")
        return {
            'meeting_id': meeting_id,
            'error': str(e),
            'status': 'failed'
        }


@celery_app.task
def generate_meeting_preparation(meeting_id: int, twin_id: int, meeting_context: Dict):
    """Generate meeting preparation materials"""
    try:
        generator = RAGResponseGenerator(twin_id)
        
        # Generate talking points
        prep_query = f"""
        Based on the meeting context: {meeting_context}
        Generate key talking points and questions for this meeting.
        """
        
        talking_points = generator.generate_response(prep_query)
        
        return {
            'meeting_id': meeting_id,
            'talking_points': talking_points,
            'status': 'completed'
        }
        
    except Exception as e:
        print(f"Error generating preparation: {e}")
        return {
            'meeting_id': meeting_id,
            'error': str(e),
            'status': 'failed'
        }