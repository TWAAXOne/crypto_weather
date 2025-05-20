import json
import pyperclip

def placeholder(content, date, link, note):
    print("Traitement de l'article...")
    print(f"- Content (début) : {content[:50]}...")
    print(f"- Date : {date}")
    print(f"- Link : {link}")
    print(f"- Note : {note}")
    print("Appel de la fonction terminé.\n")

def process_json_with_prompt(json_file, prompt_text):
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier JSON : {e}")
        return

    for i, item in enumerate(data):
        content = item.get('content', '')
        date = item.get('date', '')
        link = item.get('link', '')

        full_text = f"{prompt_text}\n\n{content}"
        pyperclip.copy(full_text)
        print(f"\nArticle {i+1}/{len(data)} copié dans le presse-papiers.")
        print("Collez-le (Ctrl+V) si vous voulez vérifier.")

        while True:
            try:
                note = float(input("Entrez une note pour cet article : "))
                break
            except ValueError:
                print("⚠️ Entrée invalide. Veuillez entrer un nombre.")

        placeholder(content, date, link, note)

    print("Tous les articles ont été traités.")

process_json_with_prompt("articles.json", "Voici un article, donne-lui une note de pertinence :")
