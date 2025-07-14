
import json
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

def compare_followers(old_data: Dict, new_data: Dict) -> Dict:
    """
    Compares two snapshots of follower/following data and identifies changes.
    old_data and new_data should be dictionaries containing:
    - 'followers_count': int
    - 'following_count': int
    - 'followers_list': JSON string of list of usernames (optional)
    - 'following_list': JSON string of list of usernames (optional)
    """
    diff = {
        'new_followers': [],
        'unfollowers': [],
        'potential_blockers': [],
        'followers_count_change': new_data.get('followers_count', 0) - old_data.get('followers_count', 0),
        'following_count_change': new_data.get('following_count', 0) - old_data.get('following_count', 0),
    }

    old_followers = set(json.loads(old_data.get('followers_list', '[]')))
    new_followers = set(json.loads(new_data.get('followers_list', '[]')))
    old_following = set(json.loads(old_data.get('following_list', '[]')))
    new_following = set(json.loads(new_data.get('following_list', '[]')))

    # Identify new followers
    diff['new_followers'] = list(new_followers - old_followers)

    # Identify unfollowers
    diff['unfollowers'] = list(old_followers - new_followers)

    # Identify potential blockers (if someone unfollows AND you no longer follow them)
    # This is a simplified logic. More robust logic might involve checking if they are still following you.
    # For now, if they unfollowed you and you no longer follow them, it's a potential blocker.
    # This part needs actual follower/following lists to be scraped, which is complex.
    # For now, we'll use a placeholder or rely on count changes.
    if diff['followers_count_change'] < 0 and abs(diff['followers_count_change']) > len(diff['unfollowers']):
        # If the count dropped more than the identified unfollowers, it might be a blocker
        # This is a very rough heuristic without actual lists.
        pass # Placeholder for more advanced blocker detection

    logger.info(f"Follower comparison: New={len(diff['new_followers'])}, Unfollowers={len(diff['unfollowers'])}, Followers Change={diff['followers_count_change']}")

    return diff


