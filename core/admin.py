ADMIN_IDS = [
    8762706702
]


def is_admin(user_id: int):
    return user_id in ADMIN_IDS