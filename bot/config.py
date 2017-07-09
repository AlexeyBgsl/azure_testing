"""
Application configuration
"""

CONFIG = {
    'LOGFMT': '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    'ACCESS_TOKEN': 'EAAUEkHk0iswBAMq2jCxGo9BxX5z5wdo74oUF64ZC0Lim6rP6BAOgCwwDoJ2wtYBD7Vrw6ZBfUgweLacbgwv8zUJa6agoOb8aSnyLzA6GkZAYVY5dprNt0QXfZA0GjKOZBGBZBGmz4OnSOmWboNbrwZBg79kpmY5MPmgPw1RMVfT40D8xdu5FZBmt',
    'VERIFY_TOKEN': 'loc@no',
    'PROJECT_ID': 'locano-172715'
}

def is_correct_token(token):
    """ Validation tocken check """
    return token == CONFIG['VERIFY_TOKEN']