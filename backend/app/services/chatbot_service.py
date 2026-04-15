"""Chatbot service for article summarization and advanced search using Ollama AI."""

import asyncio
from typing import List, Dict, Optional
from .. import state
from .ai_service import AIService
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import logging

logger = logging.getLogger(__name__)

class ChatbotService:
    """Service for handling chatbot queries using Ollama AI."""
    
    def __init__(self):
        self.ai_service = AIService()
        self.vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
        self.article_vectors = None
        self.articles = []
        self._build_index()
    
    def _build_index(self):
        """Build search index from available articles."""
        if not state.articles:
            return
        
        self.articles = list(state.articles.values())
        if not self.articles:
            return
        
        # Combine title and content for search
        texts = [f"{article.get('title', '')} {article.get('content', '')}" 
                for article in self.articles]
        
        try:
            self.article_vectors = self.vectorizer.fit_transform(texts)
        except ValueError:
            self.article_vectors = None
    
    def search_articles(self, query: str, topic: Optional[str] = None, 
                       keywords: Optional[List[str]] = None, top_k: int = 5) -> List[Dict]:
        """Search articles relevant to the user query with filters."""
        if not self.articles or self.article_vectors is None:
            return []
        
        try:
            query_vector = self.vectorizer.transform([query])
            similarities = cosine_similarity(query_vector, self.article_vectors)[0]
            
            # Filter by topic if provided
            filtered_indices = list(range(len(self.articles)))
            if topic:
                filtered_indices = [
                    i for i in filtered_indices 
                    if self.articles[i].get('topic') == topic or 
                       any(t in self.articles[i].get('category', []) for t in [topic])
                ]
            
            # Filter by keywords if provided
            if keywords:
                filtered_indices = [
                    i for i in filtered_indices
                    if any(kw.lower() in (self.articles[i].get('title', '') + 
                           self.articles[i].get('content', '')).lower() for kw in keywords)
                ]
            
            # Get top matches from filtered results
            if filtered_indices:
                filtered_similarities = [(i, similarities[i]) for i in filtered_indices]
                filtered_similarities.sort(key=lambda x: x[1], reverse=True)
                top_indices = [i for i, _ in filtered_similarities[:top_k]]
            else:
                top_indices = np.argsort(similarities)[-top_k:][::-1]
            
            results = []
            for idx in top_indices:
                if similarities[idx] > 0:
                    article = self.articles[idx]
                    results.append({
                        'id': article.get('id'),
                        'title': article.get('title'),
                        'snippet': article.get('content', '')[:300] + '...',
                        'url': article.get('url'),
                        'topic': article.get('topic'),
                        'similarity': float(similarities[idx])
                    })
            return results
        except Exception as e:
            print(f"Search error: {e}")
            return []
    
    async def call_ollama(self, prompt: str, max_tokens: int = 500) -> str:
        """Call Ollama AI for text generation."""
        try:
            return await self.ai_service._call_ai(prompt)
        except Exception as e:
            logger.error(f"Ollama AI error: {e}")
            return f"Error calling Ollama AI: {str(e)}"
    
    async def summarize_article(self, article_content: str, article_title: str) -> str:
        """Summarize an article using Ollama AI."""
        prompt = f"""Please provide a concise summary (3-4 sentences) of the following article:

Title: {article_title}

Content:
{article_content[:2000]}

Summary:"""
        
        return await self.call_ollama(prompt, max_tokens=300)
    
    async def search_and_compile(self, query: str, topic: Optional[str] = None, 
                          keywords: Optional[List[str]] = None, limit: int = 5) -> Dict:
        """Search and compile articles based on user request."""
        articles = self.search_articles(query, topic=topic, keywords=keywords, top_k=limit)
        
        if not articles:
            return {
                'query': query,
                'response': 'No articles found matching your criteria.',
                'articles': [],
                'count': 0
            }
        
        # Build context from articles for Ollama
        context = "Found articles:\n"
        for i, article in enumerate(articles, 1):
            context += f"{i}. {article['title']} (Topic: {article['topic']})\n"
        
        prompt = f"""User Query: {query}
        
{context}

Please provide a brief synthesis (2-3 sentences) of how these articles relate to the user's request."""
        
        synthesis = await self.call_ollama(prompt, max_tokens=200)
        
        return {
            'query': query,
            'filters': {
                'topic': topic,
                'keywords': keywords
            },
            'synthesis': synthesis,
            'articles': articles,
            'count': len(articles)
        }

# Create global chatbot instance
chatbot = ChatbotService()
