user_states = {}
user_stats = {}

def get_user_state(user_id):
    return user_states.get(user_id)

def set_user_state(user_id, state):
    user_states[user_id] = state

def reset_user_state(user_id):
    user_states.pop(user_id, None)

def get_user_stats(user_id):
    return user_stats.get(user_id, {})

def update_stats(user_id, subject, correct, total):
    stats = user_stats.setdefault(user_id, {}).setdefault(subject, {"correct": 0, "total": 0})
    stats["correct"] += correct
    stats["total"] += total

def reset_stats(user_id):
    user_stats.pop(user_id, None)
