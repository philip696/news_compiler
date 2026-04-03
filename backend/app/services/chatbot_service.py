"""Chatbot service for article summarization and advanced search using DeepSeek AI."""

import os
from typing import List, Dict, Optional
import httpx
from .. import state
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class ChatbotService:
    """Service for handling chatbot queries using DeepSeek AI."""
    
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.api_url = "https://api.deepseek.com/chat/completions"
        self.model = "deepseek-chat"
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
    
    def call_deepseek(self, prompt: str, max_tokens: int = 500) -> str:
        """Call DeepSeek API for text generation."""
        if not self.api_key:
            return "DeepSeek API key not configured."
        
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant that summarizes articles and provides insights based on news content."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": max_tokens
            }
            
            with httpx.Client() as client:
                response = client.post(self.api_url, json=payload, headers=headers, timeout=30.0)
                response.raise_for_status()
                
                data = response.json()
                if 'choices' in data and len(data['choices']) > 0:
                    return data['choices'][0]['message']['content']
                else:
                    return "No response from DeepSeek API."
        except Exception as e:
            print(f"DeepSeek API error: {e}")
            return f"Error calling DeepSeek: {str(e)}"
    
    def summarize_article(self, article_content: str, article_title: str) -> str:
        """Summarize an article using DeepSeek AI."""
        prompt = f"""Please provide a concise summary (3-4 sentences) of the following article:

Title: {article_title}

Content:
{article_content[:2000]}

Summary:"""
        
        return self.call_deepseek(prompt, max_tokens=300)
    
    def search_and_compile(self, query: str, topic: Optional[str] = None, 
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
        
        # Build context from articles for DeepSeek
        context = "Found articles:\n"
        for i, article in enumerate(articles, 1):
            context += f"{i}. {article['title']} (Topic: {article['topic']})\n"
        
        prompt = f"""User Query: {query}
        
{context}

Please provide a brief synthesis (2-3 sentences) of how these articles relate to the user's request."""
        
        synthesis = self.call_deepseek(prompt, max_tokens=200)
        
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
