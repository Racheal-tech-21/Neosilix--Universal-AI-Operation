"""
NEOSILIX ADVANCED AI ASSISTANT
Enhanced Universal AI Assistant with User Message History, Database Integration & Advanced Analytics
THIS PROPERTY BELONGS TO RACHEAL SILILO ONLY. DO NOT DUPLICATE. RESPECT LICENSE THANK YOU.
"""

from openai import OpenAI
from openai import RateLimitError, AuthenticationError, APIError
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
import os
import json
import threading
from collections import defaultdict, deque
import pickle
from pathlib import Path
import re
import redis
from functools import wraps
import hashlib
import time

logger = logging.getLogger(__name__)

class SecurityException(Exception):
    """Custom security exception for AI assistant"""
    pass

class AdvancedConfig:
    """Configuration manager for the AI assistant"""
    
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.max_history_per_user = int(os.getenv("MAX_HISTORY_PER_USER", "50"))
        self.enable_telemetry = os.getenv("ENABLE_TELEMETRY", "true").lower() == "true"
        self.cache_ttl = int(os.getenv("CACHE_TTL", "3600"))  # 1 hour
        self.security_level = os.getenv("SECURITY_LEVEL", "high")
        
        # Performance settings
        self.max_tokens = 1200
        self.temperature = 0.7
        self.model = "gpt-3.5-turbo"

class AdvancedSecurityManager:
    """Enhanced security manager for AI assistant operations"""
    
    def __init__(self):
        self.suspicious_patterns = [
            r'(?i)(password|secret|key|token|auth)',
            r'(?i)(drop\s+table|delete\s+from|insert\s+into)',
            r'(?i)(system32|/etc/passwd|\.\./)',
            r'(?i)(<script|javascript:)'
        ]
        self.rate_limits = defaultdict(lambda: deque(maxlen=30))
        self.max_requests_per_minute = 30
        
    def validate_input(self, user_input: str, user_context: Dict = None) -> bool:
        """Validate user input for security threats"""
        if not user_input or len(user_input) > 10000:
            raise SecurityException("Input validation failed: empty or too long")
            
        # Check for suspicious patterns
        for pattern in self.suspicious_patterns:
            if re.search(pattern, user_input):
                raise SecurityException(f"Security violation detected: suspicious pattern '{pattern}'")
        
        # Rate limiting
        user_id = user_context.get('user_id', 'anonymous') if user_context else 'anonymous'
        if self._is_rate_limited(user_id):
            raise SecurityException("Rate limit exceeded")
            
        return True
    
    def _is_rate_limited(self, user_id: str) -> bool:
        """Check if user has exceeded rate limits"""
        now = time.time()
        user_queue = self.rate_limits[user_id]
        
        # Remove requests older than 1 minute
        while user_queue and now - user_queue[0] > 60:
            user_queue.popleft()
            
        if len(user_queue) >= self.max_requests_per_minute:
            return True
            
        user_queue.append(now)
        return False
    
    def sanitize_response(self, response: str) -> str:
        """Sanitize AI response to prevent injection attacks"""
        # Remove potential script tags
        response = re.sub(r'<script.*?</script>', '', response, flags=re.IGNORECASE | re.DOTALL)
        # Remove dangerous HTML
        response = re.sub(r'<.*?javascript:.*?>', '', response, flags=re.IGNORECASE)
        return response

class AdvancedCacheManager:
    """Intelligent caching system for AI responses"""
    
    def __init__(self, redis_url: str):
        try:
            self.redis_client = redis.from_url(redis_url, socket_connect_timeout=1, socket_timeout=1)
            self.redis_client.ping()
            self.connected = True
        except:
            self.redis_client = None
            self.connected = False
            logger.warning("Redis not available, using in-memory cache")
            
        self.memory_cache = {}
        self.hits = 0
        self.misses = 0
    
    def get_cache_key(self, question: str, context_hash: str) -> str:
        """Generate cache key from question and context"""
        content = f"{question}:{context_hash}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            if self.connected:
                cached = self.redis_client.get(key)
                if cached:
                    self.hits += 1
                    return pickle.loads(cached)
            else:
                if key in self.memory_cache:
                    self.hits += 1
                    return self.memory_cache[key]
                    
            self.misses += 1
            return None
        except:
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600):
        """Set value in cache"""
        try:
            if self.connected:
                self.redis_client.setex(key, ttl, pickle.dumps(value))
            else:
                self.memory_cache[key] = value
        except:
            pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': round(hit_rate, 2),
            'redis_connected': self.connected,
            'memory_cache_size': len(self.memory_cache)
        }

class AdvancedAnalyticsManager:
    """Advanced analytics for AI assistant usage"""
    
    def __init__(self):
        self.usage_stats = defaultdict(lambda: {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_tokens': 0,
            'response_times': [],
            'question_types': defaultdict(int)
        })
        self.popular_questions = defaultdict(int)
    
    def log_request(self, user_id: str, question: str, question_type: str, 
                   success: bool, tokens_used: int, response_time: float):
        """Log AI assistant request"""
        user_stats = self.usage_stats[user_id]
        user_stats['total_requests'] += 1
        
        if success:
            user_stats['successful_requests'] += 1
            user_stats['total_tokens'] += tokens_used
            user_stats['response_times'].append(response_time)
            user_stats['question_types'][question_type] += 1
            
            # Track popular questions
            question_key = question.lower()[:100]
            self.popular_questions[question_key] += 1
        else:
            user_stats['failed_requests'] += 1
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get statistics for a specific user"""
        stats = self.usage_stats.get(user_id, {})
        if not stats:
            return {}
            
        response_times = stats.get('response_times', [])
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            'total_requests': stats['total_requests'],
            'success_rate': (stats['successful_requests'] / stats['total_requests'] * 100) if stats['total_requests'] > 0 else 0,
            'average_response_time': round(avg_response_time, 2),
            'total_tokens_used': stats['total_tokens'],
            'favorite_question_types': dict(sorted(stats['question_types'].items(), key=lambda x: x[1], reverse=True)[:5])
        }
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get overall system statistics"""
        total_users = len(self.usage_stats)
        total_requests = sum(stats['total_requests'] for stats in self.usage_stats.values())
        total_tokens = sum(stats['total_tokens'] for stats in self.usage_stats.values())
        
        # Most popular questions
        top_questions = sorted(self.popular_questions.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'total_users': total_users,
            'total_requests': total_requests,
            'total_tokens_used': total_tokens,
            'top_questions': [{'question': q, 'count': c} for q, c in top_questions],
            'average_requests_per_user': round(total_requests / total_users, 2) if total_users > 0 else 0
        }

class UserConversationManager:
    """Enhanced conversation manager with persistence and analytics"""
    
    def __init__(self, max_history_per_user: int = 50, persistence_path: str = "conversation_history"):
        self.max_history_per_user = max_history_per_user
        self.persistence_path = Path(persistence_path)
        self.persistence_path.mkdir(exist_ok=True)
        
        # In-memory storage with user_id -> deque of messages
        self.user_conversations = defaultdict(lambda: deque(maxlen=max_history_per_user))
        self.lock = threading.Lock()
        
        # Load existing conversations
        self._load_persisted_conversations()
    
    def add_message(self, user_id: str, role: str, content: str, metadata: Dict = None):
        """Add a message to user's conversation history"""
        with self.lock:
            message = {
                'role': role,
                'content': content,
                'timestamp': datetime.now().isoformat(),
                'metadata': metadata or {}
            }
            
            self.user_conversations[user_id].append(message)
            
            # Persist after adding
            self._persist_user_conversation(user_id)
    
    def get_conversation_history(self, user_id: str, max_messages: int = None) -> List[Dict]:
        """Get conversation history for a user"""
        with self.lock:
            history = list(self.user_conversations.get(user_id, deque()))
            if max_messages:
                history = history[-max_messages:]
            return history
    
    def get_recent_context(self, user_id: str, num_exchanges: int = 3) -> List[Dict]:
        """Get recent conversation context for continuity"""
        history = self.get_conversation_history(user_id)
        # Return last N exchanges (2 messages per exchange)
        return history[-(num_exchanges * 2):] if history else []
    
    def clear_user_history(self, user_id: str):
        """Clear conversation history for a user"""
        with self.lock:
            if user_id in self.user_conversations:
                self.user_conversations[user_id].clear()
                self._persist_user_conversation(user_id)
    
    def get_conversation_stats(self, user_id: str) -> Dict[str, Any]:
        """Get statistics for user's conversation history"""
        history = self.get_conversation_history(user_id)
        if not history:
            return {}
            
        user_messages = [msg for msg in history if msg['role'] == 'user']
        assistant_messages = [msg for msg in history if msg['role'] == 'assistant']
        
        return {
            'total_messages': len(history),
            'user_messages': len(user_messages),
            'assistant_messages': len(assistant_messages),
            'first_interaction': history[0]['timestamp'] if history else None,
            'last_interaction': history[-1]['timestamp'] if history else None,
            'average_user_message_length': sum(len(msg['content']) for msg in user_messages) / len(user_messages) if user_messages else 0
        }
    
    def _persist_user_conversation(self, user_id: str):
        """Persist user conversation to disk"""
        try:
            user_file = self.persistence_path / f"{user_id}.json"
            history = list(self.user_conversations[user_id])
            
            with open(user_file, 'w') as f:
                json.dump({
                    'user_id': user_id,
                    'last_updated': datetime.now().isoformat(),
                    'history': history
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to persist conversation for user {user_id}: {e}")
    
    def _load_persisted_conversations(self):
        """Load persisted conversations from disk"""
        try:
            for user_file in self.persistence_path.glob("*.json"):
                try:
                    with open(user_file, 'r') as f:
                        data = json.load(f)
                        user_id = data['user_id']
                        history = data.get('history', [])
                        
                        # Load into memory (respect max history)
                        self.user_conversations[user_id].extend(history[-self.max_history_per_user:])
                        
                except Exception as e:
                    logger.error(f"Failed to load conversation file {user_file}: {e}")
        except Exception as e:
            logger.error(f"Failed to load persisted conversations: {e}")

class QuickResponseEngine:
    """Fast, non-dull response engine for common queries"""
    
    def __init__(self):
        # Pre-compiled patterns for speed - FIXED TARGETS STATUS
        self.patterns = {
            'targets_status': re.compile(r'(?i)(show|list|display|view|get).*targets|(targets?|devices?|hosts?)\s+(status|health|list|overview|how many)|(all\s+)?targets'),
            'targets_create': re.compile(r'(?i)(add|create|new)\s+(target|device|host|monitor)'),
            'system_status': re.compile(r'(?i)(system|server)\s+(health|status|performance)'),
            'anomaly': re.compile(r'(?i)(anomaly|issue|problem|error|what.s? wrong|trouble)'),
            'performance': re.compile(r'(?i)(slow|fast|performance|optimize|speed)')
        }
    
    def get_quick_response(self, question: str, system_metrics: Dict, targets_data: List[Dict]) -> Optional[str]:
        """Provide instant, non-dull responses for common queries"""
        question_lower = question.lower()
        
        if self.patterns['targets_status'].search(question_lower):
            return self._get_targets_status(targets_data)
        elif self.patterns['system_status'].search(question_lower):
            return self._get_system_status(system_metrics)
        elif self.patterns['anomaly'].search(question_lower):
            return self._get_anomaly_status(targets_data)
        elif self.patterns['performance'].search(question_lower):
            return self._get_performance_status(system_metrics)
        
        return None
    
    def _get_targets_status(self, targets_data: List[Dict]) -> str:
        """Instant targets overview - NO TARGET CREATION MENTION"""
        if not targets_data:
            return "🎯 **MONITORING TARGETS**: No targets configured"
        
        total = len(targets_data)
        healthy = len([t for t in targets_data if t.get('status') == 'healthy'])
        warning = len([t for t in targets_data if t.get('status') == 'warning'])
        offline = len([t for t in targets_data if t.get('status') == 'offline'])
        
        health_score = int((healthy / total) * 100) if total > 0 else 100
        
        response = f"""🎯 **MONITORING TARGETS**: {health_score}% Health
• Total: {total} | ✅ Healthy: {healthy} | ⚠️ Warning: {warning} | 🔴 Offline: {offline}"""

        # Show critical targets
        critical_targets = [t for t in targets_data if t.get('status') in ['offline', 'warning'] and t.get('priority') in ['high', 'critical']][:3]
        if critical_targets:
            response += "\n\n🚨 **Critical Targets**:"
            for target in critical_targets:
                response += f"\n• {target.get('name')} - {target.get('status').upper()}"

        return response
    
    def _get_system_status(self, system_metrics: Dict) -> str:
        """Instant system status"""
        cpu = system_metrics.get('cpu', 0)
        memory = system_metrics.get('memory', 0)
        disk = system_metrics.get('disk', 0)
        
        status = "🟢 Optimal" if cpu < 80 else "🟡 Loaded" if cpu < 90 else "🔴 Critical"
        
        return f"""⚡ **SYSTEM STATUS**: {status}
• CPU: {cpu}% | Memory: {memory}% | Disk: {disk}%
• Alerts: {system_metrics.get('active_alerts', 0)} active
• Zabbix: {'✅ Connected' if system_metrics.get('zabbix_connected') else '❌ Disconnected'}"""
    
    def _get_anomaly_status(self, targets_data: List[Dict]) -> str:
        """Instant anomaly detection"""
        anomalies = [t for t in targets_data if t.get('status') in ['offline', 'warning']] if targets_data else []
        
        if not anomalies:
            return "✅ **ANOMALY STATUS**: No anomalies detected - all systems normal"
        
        response = f"🚨 **ANOMALIES DETECTED**: {len(anomalies)} targets need attention\n"
        for target in anomalies[:5]:
            response += f"• {target.get('name')} - {target.get('status').upper()}\n"
        
        return response
    
    def _get_performance_status(self, system_metrics: Dict) -> str:
        """Performance status"""
        cpu = system_metrics.get('cpu', 0)
        memory = system_metrics.get('memory', 0)
        
        if cpu > 85 or memory > 90:
            return "🔧 **PERFORMANCE**: System under load - consider optimization"
        else:
            return "✅ **PERFORMANCE**: System running optimally"

class NeosilixAdvancedAIAssistant:
    """
    NEOSILIX ADVANCED AI ASSISTANT
    Enhanced Universal AI Assistant with User Message History, Database Integration & Advanced Analytics
    """
    
    def __init__(self):
        self.config = AdvancedConfig()
        self.security = AdvancedSecurityManager()
        self.cache = AdvancedCacheManager(self.config.redis_url)
        self.analytics = AdvancedAnalyticsManager()
        self.conversation_manager = UserConversationManager(
            max_history_per_user=self.config.max_history_per_user
        )
        self.quick_engine = QuickResponseEngine()
        
        # Initialize OpenAI client
        self.openai_client = None
        if self.config.openai_api_key:
            try:
                self.openai_client = OpenAI(api_key=self.config.openai_api_key)
                logger.info("OpenAI client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
        
        # Updated Question classification patterns - FIXED TARGETS STATUS
        self.question_patterns = {
            'system_health': [
                r'(?i)(system|server)\s+(health|status|performance)',
                r'(?i)(how\s+is\s+.*\s+doing)',
                r'(?i)(check|show)\s+(system|server)',
                r'(?i)(cpu|memory|disk)\s+(usage|utilization)'
            ],
            'monitoring_targets': [
                r'(?i)(show|list|display|view|get).*targets',
                r'(?i)(targets?|devices?|hosts?)\s+(status|health|list|overview|how many)',
                r'(?i)(monitoring)\s+(targets?|devices?)',
                r'(?i)(how many.*targets?)',
                r'(?i)(all\s+)?targets',  # This will catch "show me all targets"
                r'(?i)what.*targets',  # This will catch "what targets do I have"
            ],
            'target_creation': [
                r'(?i)(add|create|new)\s+(target|device|host|server)',
                r'(?i)(monitor|watch)\s+(new|additional)',
                r'(?i)(set up|configure)\s+monitoring\s+for',
                r'(?i)(ip\s+address.*add|add.*ip\s+address)'
            ],
            'anomaly_detection': [
                r'(?i)(anomaly|issue|problem|error)',
                r'(?i)(what\'s wrong|what is wrong)',
                r'(?i)(troubleshoot|diagnose)',
                r'(?i)(why.*down|why.*not working)'
            ],
            'recommendations': [
                r'(?i)(recommend|suggest|advice)',
                r'(?i)(what should I do|how can I improve)',
                r'(?i)(best practice|optimize)'
            ],
            'technical_help': [
                r'(?i)(how to|how do I)',
                r'(?i)(help me with|assist with)',
                r'(?i)(can you help|can you show)'
            ],
            'ml_system': [
                r'(?i)(ml|machine learning|ai)',
                r'(?i)(anomaly detection|prediction)',
                r'(?i)(intelligent|smart)',
                r'(?i)(self.healing|auto.heal)'
            ],
            'general_help': [
                r'(?i)(help|support|guide)',
                r'(?i)(what can you do)',
                r'(?i)(hello|hi|hey)'
            ]
        }
        
        logger.info("Neosilix Advanced AI Assistant initialized successfully")
    
    def ask_anything(self, question: str, system_metrics: Dict, 
                    user_context: Dict = None, targets_data: List[Dict] = None) -> Dict[str, Any]:
        """
        Main method to ask anything - enhanced with caching, security, and analytics
        
        Args:
            question: User's question
            system_metrics: Current system metrics
            user_context: User information including user_id and is_admin
            targets_data: List of monitoring targets for context
            
        Returns:
            Enhanced response with analytics and context
        """
        start_time = time.time()
        user_id = user_context.get('user_id', 'anonymous') if user_context else 'anonymous'
        
        try:
            # Security validation
            self.security.validate_input(question, user_context)
            
            # Try quick response first (non-dull, instant)
            quick_response = self.quick_engine.get_quick_response(question, system_metrics, targets_data or [])
            if quick_response:
                processing_time = round((time.time() - start_time) * 1000, 2)
                
                result = {
                    'response': quick_response,
                    'processing_time': processing_time,
                    'method': 'quick-engine',
                    'timestamp': datetime.now().isoformat(),
                    'question_type': 'quick',
                    'user_id': user_id,
                    'system_health': system_metrics.get('cpu', 0)
                }
                
                # Add to conversation history
                self.conversation_manager.add_message(user_id, "user", question)
                self.conversation_manager.add_message(user_id, "assistant", quick_response)
                
                return result
            
            # Check cache
            cache_key = self._generate_cache_key(question, system_metrics, user_context, targets_data)
            cached_response = self.cache.get(cache_key)
            
            if cached_response:
                logger.info(f"Cache hit for user {user_id}")
                cached_response['cached'] = True
                cached_response['cache_stats'] = self.cache.get_stats()
                return cached_response
            
            # Analyze question intent
            question_type = self._analyze_question_intent(question)
            
            # Use OpenAI for complex questions
            if self.openai_client:
                response = self._process_with_openai(question, system_metrics, user_context, targets_data or [], question_type)
            else:
                response = self._get_fallback_response(question, system_metrics, user_context, targets_data or [], question_type)
            
            return self._finalize_response(response, start_time, user_id, question_type, 
                                         system_metrics, targets_data, cache_key)
            
        except SecurityException as e:
            logger.warning(f"Security violation by user {user_id}: {e}")
            return self._create_security_response(str(e), start_time, user_id)
            
        except Exception as e:
            logger.error(f"Error processing question from user {user_id}: {e}")
            return self._create_error_response(str(e), start_time, user_id)
    
    def _analyze_question_intent(self, question: str) -> str:
        """Analyze question intent with enhanced pattern matching - FIXED TARGETS STATUS"""
        question_lower = question.lower()
        
        # Check for targets status FIRST (before creation)
        if any(re.search(pattern, question_lower) for pattern in self.question_patterns['monitoring_targets']):
            return 'monitoring_targets'
        
        # Then check for other intents
        for intent, patterns in self.question_patterns.items():
            if intent == 'monitoring_targets':  # Already checked
                continue
            for pattern in patterns:
                if re.search(pattern, question_lower):
                    return intent
        
        return 'general'
    
    def _generate_cache_key(self, question: str, system_metrics: Dict, 
                          user_context: Dict, targets_data: List[Dict]) -> str:
        """Generate cache key from question and context"""
        # Create context hash from relevant metrics
        context_data = {
            'question': question.lower(),
            'cpu': round(system_metrics.get('cpu', 0)),
            'memory': round(system_metrics.get('memory', 0)),
            'targets_count': len(targets_data) if targets_data else 0,
            'user_role': 'admin' if user_context and user_context.get('is_admin') else 'user'
        }
        
        context_hash = hashlib.md5(json.dumps(context_data, sort_keys=True).encode()).hexdigest()
        return self.cache.get_cache_key(question, context_hash)
    
    def _process_with_openai(self, question: str, system_metrics: Dict, 
                           user_context: Dict, targets_data: List[Dict], question_type: str) -> Dict[str, Any]:
        """Process question using OpenAI with enhanced context"""
        user_id = user_context.get('user_id', 'anonymous') if user_context else 'anonymous'
        
        # Build enhanced context
        system_context = self._build_system_context(system_metrics, user_context, targets_data)
        
        # Add user's conversation history for continuity
        user_history = self.conversation_manager.get_recent_context(user_id, num_exchanges=3)
        
        messages = [
            {"role": "system", "content": system_context},
            *user_history,
            {"role": "user", "content": question}
        ]
        
        # Generate response
        response = self.openai_client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Sanitize response
        response_text = self.security.sanitize_response(response_text)
        
        # Store in conversation history
        self.conversation_manager.add_message(user_id, "user", question, {
            'question_type': question_type,
            'system_health': system_metrics.get('cpu', 0)
        })
        self.conversation_manager.add_message(user_id, "assistant", response_text, {
            'processing_time': 'openai',
            'tokens_used': response.usage.total_tokens
        })
        
        return {
            'response': response_text,
            'tokens_used': response.usage.total_tokens,
            'method': f'openai-{self.config.model}'
        }
    
    def _build_system_context(self, system_metrics: Dict, user_context: Dict, targets_data: List[Dict]) -> str:
        """Build comprehensive system context for AI"""
        context = f"""You are Neosilix Advanced AI Assistant - provide CONCISE, TECHNICAL responses.

CURRENT SYSTEM STATE:
• CPU: {system_metrics.get('cpu', 0)}% | Memory: {system_metrics.get('memory', 0)}% | Disk: {system_metrics.get('disk', 0)}%
• Active Alerts: {system_metrics.get('active_alerts', 0)}
• Zabbix Connected: {system_metrics.get('zabbix_connected', False)}"""

        # Add monitoring targets information
        if targets_data:
            total_targets = len(targets_data)
            healthy_targets = len([t for t in targets_data if t.get('status') == 'healthy'])
            health_score = int((healthy_targets / total_targets) * 100) if total_targets > 0 else 100
            
            context += f"""
MONITORING TARGETS:
• Total Targets: {total_targets}
• Health Score: {health_score}%
• Healthy: {healthy_targets} | Issues: {total_targets - healthy_targets}"""

        context += f"""
RESPONSE STYLE:
- Be technical and concise
- Use bullet points for clarity  
- Include specific metrics
- Avoid unnecessary greetings
- Focus on actionable information

USER CONTEXT: {user_context.get('user_id', 'Unknown')} ({'Admin' if user_context and user_context.get('is_admin') else 'User'})"""
        
        return context
    
    def _get_fallback_response(self, question: str, system_metrics: Dict, 
                             user_context: Dict, targets_data: List[Dict], question_type: str) -> Dict[str, Any]:
        """Provide intelligent fallback when OpenAI is unavailable"""
        # Use quick engine as fallback
        quick_response = self.quick_engine.get_quick_response(question, system_metrics, targets_data)
        if quick_response:
            return {
                'response': quick_response + "\n\n(OpenAI unavailable - using quick analysis)",
                'method': 'fallback-quick',
                'tokens_used': 0
            }
        
        # Basic fallback
        base_responses = {
            'system_health': f"System health: {system_metrics.get('cpu', 0)}% CPU, {system_metrics.get('memory', 0)}% Memory",
            'monitoring_targets': f"Monitoring {len(targets_data)} targets. {len([t for t in targets_data if t.get('status') == 'healthy'])} healthy.",
            'general': "I can help with system monitoring, target management, and performance analysis."
        }
        
        response_text = base_responses.get(question_type, base_responses['general'])
        
        return {
            'response': response_text,
            'method': 'fallback-basic',
            'tokens_used': 0
        }
    
    def _finalize_response(self, response: Dict, start_time: float, user_id: str, 
                         question_type: str, system_metrics: Dict, targets_data: List[Dict], 
                         cache_key: str) -> Dict[str, Any]:
        """Finalize response with analytics and caching"""
        processing_time = round((time.time() - start_time) * 1000, 2)  # Convert to milliseconds
        
        # Add analytics
        self.analytics.log_request(
            user_id, response.get('response', '')[:100], question_type,
            True, response.get('tokens_used', 0), processing_time
        )
        
        # Build final response
        final_response = {
            'response': response['response'],
            'processing_time': processing_time,
            'method': response['method'],
            'timestamp': datetime.now().isoformat(),
            'question_type': question_type,
            'system_health': system_metrics.get('cpu', 0),
            'user_id': user_id,
            'conversation_stats': self.conversation_manager.get_conversation_stats(user_id),
            'analytics': self.analytics.get_user_stats(user_id),
            'cache_stats': self.cache.get_stats()
        }
        
        # Add tokens if available
        if 'tokens_used' in response:
            final_response['tokens_used'] = response['tokens_used']
        
        # Cache the response (if not already cached)
        if not response.get('cached', False):
            self.cache.set(cache_key, final_response, self.config.cache_ttl)
        
        return final_response
    
    def _create_security_response(self, error: str, start_time: float, user_id: str) -> Dict[str, Any]:
        """Create security violation response"""
        processing_time = round((time.time() - start_time) * 1000, 2)
        
        self.analytics.log_request(
            user_id, "SECURITY_BLOCKED", "security",
            False, 0, processing_time
        )
        
        return {
            'response': f"🚫 Security violation detected: {error}",
            'processing_time': processing_time,
            'method': 'security-block',
            'timestamp': datetime.now().isoformat(),
            'question_type': 'security',
            'user_id': user_id,
            'error': True,
            'security_block': True
        }
    
    def _create_error_response(self, error: str, start_time: float, user_id: str) -> Dict[str, Any]:
        """Create error response"""
        processing_time = round((time.time() - start_time) * 1000, 2)
        
        self.analytics.log_request(
            user_id, "ERROR", "error",
            False, 0, processing_time
        )
        
        return {
            'response': f"❌ Sorry, I encountered an error: {error}",
            'processing_time': processing_time,
            'method': 'error',
            'timestamp': datetime.now().isoformat(),
            'question_type': 'error',
            'user_id': user_id,
            'error': True
        }
    
    # Public methods for external access
    def get_user_conversation_history(self, user_id: str, max_messages: int = None) -> List[Dict]:
        """Get conversation history for a user"""
        return self.conversation_manager.get_conversation_history(user_id, max_messages)
    
    def clear_user_history(self, user_id: str):
        """Clear conversation history for a user"""
        self.conversation_manager.clear_user_history(user_id)
    
    def get_user_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get analytics for a specific user"""
        return self.analytics.get_user_stats(user_id)
    
    def get_system_analytics(self) -> Dict[str, Any]:
        """Get overall system analytics"""
        return self.analytics.get_system_stats()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self.cache.get_stats()
    
    def analyze_targets(self, targets_data: List[Dict]) -> Dict[str, Any]:
        """Analyze monitoring targets"""
        if not targets_data:
            return self._get_empty_analysis()
        
        total_targets = len(targets_data)
        healthy_targets = len([t for t in targets_data if t.get('status') == 'healthy'])
        warning_targets = len([t for t in targets_data if t.get('status') == 'warning'])
        offline_targets = len([t for t in targets_data if t.get('status') == 'offline'])
        
        health_score = int((healthy_targets / total_targets) * 100) if total_targets > 0 else 100
        
        return {
            'overview': {
                'total_targets': total_targets,
                'healthy_targets': healthy_targets,
                'warning_targets': warning_targets,
                'offline_targets': offline_targets,
                'health_score': health_score,
                'status': 'healthy' if health_score > 90 else 'warning' if health_score > 70 else 'critical'
            },
            'critical_issues': [t for t in targets_data if t.get('status') in ['offline', 'warning']],
            'analysis_timestamp': datetime.now().isoformat()
        }
    
    def get_system_insights(self, system_metrics: Dict, targets_data: List[Dict] = None) -> Dict[str, Any]:
        """Get comprehensive system insights"""
        health_score = system_metrics.get('cpu', 0)  # Simplified for now
        
        return {
            'current_health': {
                'overall_score': 100 - health_score,  # Inverted for better representation
                'component_health': {
                    'cpu': 'optimal' if health_score < 70 else 'warning' if health_score < 85 else 'critical',
                    'memory': 'optimal',
                    'disk': 'optimal'
                }
            },
            'recommendations': [
                {
                    'priority': 'low',
                    'action': 'System running optimally',
                    'details': 'No immediate actions required'
                }
            ],
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_empty_analysis(self) -> Dict[str, Any]:
        """Return empty analysis structure"""
        return {
            'overview': {
                'total_targets': 0,
                'healthy_targets': 0,
                'warning_targets': 0,
                'offline_targets': 0,
                'health_score': 100,
                'status': 'healthy'
            },
            'critical_issues': [],
            'analysis_timestamp': datetime.now().isoformat()
        }

# Global instance for easy import
neosilix_assistant = NeosilixAdvancedAIAssistant()

# Compatibility functions - ADDED MISSING analyze_monitoring_targets FUNCTION
def ask_anything(question: str, system_metrics: Dict, user_context: Dict = None, targets_data: List[Dict] = None) -> Dict[str, Any]:
    """Main compatibility function"""
    return neosilix_assistant.ask_anything(question, system_metrics, user_context, targets_data)

def get_user_conversation_history(user_id: str, max_messages: int = None) -> List[Dict]:
    """Get user conversation history"""
    return neosilix_assistant.get_user_conversation_history(user_id, max_messages)

def clear_user_conversation_history(user_id: str):
    """Clear user conversation history"""
    neosilix_assistant.clear_user_history(user_id)

def analyze_monitoring_targets(targets_data: List[Dict]) -> Dict[str, Any]:
    """Analyze monitoring targets - ADDED MISSING FUNCTION"""
    return neosilix_assistant.analyze_targets(targets_data)

def get_system_insights(system_metrics: Dict, targets_data: List[Dict] = None) -> Dict[str, Any]:
    """Get system insights"""
    return neosilix_assistant.get_system_insights(system_metrics, targets_data)

# Initialize the assistant
if __name__ == "__main__":
    print("Neosilix Advanced AI Assistant initialized successfully")
    print(f"OpenAI configured: {neosilix_assistant.openai_client is not None}")
    print(f"Redis connected: {neosilix_assistant.cache.connected}")
    print(f"Security level: {neosilix_assistant.config.security_level}")
