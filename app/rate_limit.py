from datetime import datetime, timedelta
import redis
import logging

logger = logging.getLogger(__name__)

class TierRateLimiter:
    """Rate limiter based on subscription tier"""
    
    # Rate limits per tier (requests per day)
    LIMITS = {
        "free": 11,
    }
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
    
    def check_rate_limit(self, user_id: str, tier: str) -> tuple[bool, dict]:
        """
        Check if user has exceeded rate limit.
        
        Returns:
            (is_allowed, info_dict)
        """
        
        key = f"user:{user_id}:calls"
        today = datetime.utcnow().date()
        key_with_date = f"{key}:{today}"
        
        try:
            # Get current count
            current_count = self.redis_client.get(key_with_date)
            current_count = int(current_count) if current_count else 0
            
            # Get limit for tier
            limit = self.LIMITS.get(tier, self.LIMITS["free"])
            
            # Check if exceeded
            if current_count >= limit:
                return False, {
                    "limit": limit,
                    "current": current_count,
                    "remaining": 0,
                    "reset_at": str(datetime.utcnow() + timedelta(days=1))
                }
            
            # Increment counter (expires in 24 hours)
            self.redis_client.incr(key_with_date)
            self.redis_client.expire(key_with_date, 86400)  # 24 hours
            
            return True, {
                "limit": limit,
                "current": current_count + 1,
                "remaining": limit - (current_count + 1),
                "reset_at": str(datetime.utcnow() + timedelta(days=1))
            }
        
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            # On error, allow request but log it
            return True, {"error": str(e)}