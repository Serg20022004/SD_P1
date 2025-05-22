# insult_getter_redis.py
import redis

REDIS_HOST = 'localhost'
REDIS_PORT = 6379
INSULTS_SET_KEY = 'insults_set'

def get_all_insults_from_redis():
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
        
        # SMEMBERS returns all members of the set
        all_insults = r.smembers(INSULTS_SET_KEY)
        
        if all_insults:
            print("Current insults stored in Redis:")
            for i, insult in enumerate(sorted(list(all_insults))): # Sort for consistent display
                print(f"  {i+1}. {insult}")
        else:
            print("No insults found in Redis.")
            
    except redis.exceptions.ConnectionError as e:
        print(f"Error: Could not connect to Redis at {REDIS_HOST}:{REDIS_PORT} - {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    get_all_insults_from_redis()
