_users_state = {}
_users_stats = {}

def get_user_state(user_id):
    return _users_state.get(user_id)

def set_user_state(user_id, state):
    _users_state[user_id] = state

def reset_user_state(user_id):
    if user_id in _users_state:
        del _users_state[user_id]

def update_stats(user_id, subject, score, total):
    stats = _users_stats.setdefault(user_id, {})
    subject_stats = stats.setdefault(subject, {"score": 0, "total": 0})
    subject_stats["score"] += score
    subject_stats["total"] += total

def reset_stats(user_id):
    if user_id in _users_stats:
        del _users_stats[user_id]
