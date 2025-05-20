import emoji

def remove_emojis(text):
    """Supprime tous les emojis d'un texte."""
    if not isinstance(text, str):
        return text
    return emoji.replace_emoji(text, replace='')