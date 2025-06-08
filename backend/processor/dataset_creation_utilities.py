import pyperclip
import h5_utilities

def addNoteToDataset(index, content, link, date, crypto, note, dataset):
    h5_utilities.updateArticleDataset(index,content,link,date,crypto,note,dataset,True)
    print(h5_utilities.getArticleDataset(index,dataset, isTrainDataset=True))

def process_dataset_with_prompt(dataset, prompt_text):

    lenDataset = h5_utilities.getDatasetLength(dataset)

    for i in range(0,lenDataset):
        content, link, date, crypto, note = h5_utilities.getArticleDataset(i,dataset, isTrainDataset=True)

        full_text = f"{prompt_text}\n\n{content}"
        print(full_text)
        pyperclip.copy(full_text)
        print(f"\nArticle {i+1}/{lenDataset} copié dans le presse-papiers.")
        print("Collez-le (Ctrl+V) si vous voulez vérifier.")

        while True:
            try:
                note = float(input("Entrez une note pour cet article : "))
                break
            except ValueError:
                print("Entrée invalide. Veuillez entrer un nombre.")

        addNoteToDataset(i, content, link, date, crypto, note, dataset)

    print("Tous les articles ont été traités.")

if __name__ == "__main__":
    prompt = "Analyse le texte suivant et évalue le sentiment global à propos des cryptomonnaies sur une échelle de -1 à 1, où :\n-1 représente une peur extrême (panic sell, crash, effondrement, incertitude totale),\n0 représente un sentiment neutre ou incertain,\n1 représente une avidité extrême (euphorie, FOMO, croissance explosive, confiance excessive).\nDonne uniquement la note chiffrée sur cette échelle, suivie d'une justification expliquant ton choix.\nVoici le texte à analyser :\n\n"
    process_dataset_with_prompt("test_dataset", prompt)
