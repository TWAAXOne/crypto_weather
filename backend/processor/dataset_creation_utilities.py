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
    prompt = "Voici un article, donne-lui une note de pertinence : "
    process_dataset_with_prompt("dataset", prompt)
