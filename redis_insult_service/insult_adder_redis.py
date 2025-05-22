# insult_adder_redis.py
import redis
import sys

REDIS_HOST = 'localhost'
REDIS_PORT = 6379
INSULTS_SET_KEY = 'insults_set'

def add_insult_to_redis(insult_text):
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
        
        # SADD returns 1 if element is added, 0 if element already exists
        if r.sadd(INSULTS_SET_KEY, insult_text):
            print(f"Added insult: '{insult_text}'")
            return True
        else:
            print(f"Insult '{insult_text}' already exists in Redis.")
            return False
    except redis.exceptions.ConnectionError as e:
        print(f"Error: Could not connect to Redis at {REDIS_HOST}:{REDIS_PORT} - {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False

if __name__ == "__main__":
    default_insults = [
        "If you were a spice, you'd be flour.",
        "You bring everyone a lot of joy when you leave the room.",
        "I'd call you a tool, but even they serve a purpose.",
        "If you were a spice, you'd be flour." # Duplicate
    ]

    insults_to_process = default_insults
    if len(sys.argv) > 1: # Allow passing insults as command line arguments
        insults_to_process = sys.argv[1:]
        print(f"Adding insults from command line arguments: {insults_to_process}")
    else:
        print(f"Adding default insults.")

    added_count = 0
    for insult in insults_to_process:
        if add_insult_to_redis(insult):
            added_count += 1
    
    print(f"\nFinished adding insults. {added_count} new insults were added to Redis.")
