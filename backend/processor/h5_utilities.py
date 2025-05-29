import os
import h5py
import numpy as np

def checkDatasetExist(datasetFileName):
    """
    Vérifie si le dataset au format h5 existe.

    Arguments :
    - datasetFileName (str) : Nom du dataset sans l'extension.
    Résultat :
    - True si le dataset existe.    
    - False si inexistant.
    """
    if not os.path.exists(datasetFileName + ".h5"):
        return False
    return True

def createDataset(content, link, date, crypto, note, datasetFileName="dataset"):
    if checkDatasetExist(datasetFileName):
        print(f"Erreur : Le fichier {datasetFileName}.h5 existe déjà.")
        return

    # Encodage en array d'objets
    crypto = np.array([",".join(c) for c in crypto], dtype='S')

    with h5py.File(datasetFileName + ".h5", 'w') as f:
        f.create_dataset('content', data=content, compression="gzip", chunks=True, maxshape=(None,))
        f.create_dataset('link', data=link, compression="gzip", chunks=True, maxshape=(None,))
        f.create_dataset('date', data=date, compression="gzip", chunks=True, maxshape=(None,))
        f.create_dataset('crypto', data=crypto, compression="gzip", chunks=True, maxshape=(None,))
        f.create_dataset('note', data=note, compression="gzip", chunks=True, maxshape=(None,))


        # Optionnel : Ajouter des métadonnées pour mieux organiser
        f.attrs['description'] = 'Dataset d\'articles pour classification'
        f.attrs['source'] = 'Internet : \n - https://crypto.news/markets/ \n - https://u.today/latest-cryptocurrency-news \n - https://beincrypto.com/news/ '
        f.attrs['placeholderContent'] = True
        f.attrs['last_news_cryptoNews'] = 'None'
        f.attrs['last_news_uToday'] = 'None'
        f.attrs['last_news_beInCrypto'] = 'None'

def remove_first_item(datasetFileName="dataset"):
    """
    Do not run if dataset have only the placeholder entry !
    """
    with h5py.File(datasetFileName + ".h5", 'r+') as f:
        for name in f.keys():
            print(f"Traitement du dataset : {name}")
            dset = f[name]
            
            dset[:len(dset)-1] = dset[1:]
            
            dset.resize((len(dset) - 1,))
        

def appendArticleToDataset(new_content, new_link, new_date, new_crypto, new_note, datasetFileName="dataset"):
    if not checkDatasetExist(datasetFileName):
        print(f"Erreur : Le fichier {datasetFileName}.h5 n'existe pas.")
        return

    with h5py.File(datasetFileName + ".h5", 'a') as f:
        # Convertir en format encodé
        new_content_b = np.array([new_content.encode('utf-8')])
        new_link_b = np.array([new_link.encode('utf-8')])
        new_date_b = np.array([new_date.encode('utf-8')])
        new_crypto_b = np.array([",".join(new_crypto).encode('utf-8')])
        new_note_f = np.array([new_note])

        # Pour chaque dataset, on étend la taille et on ajoute la nouvelle valeur
        for name, new_data in zip(
            ['content', 'link', 'date', 'crypto', 'note'],
            [new_content_b, new_link_b, new_date_b, new_crypto_b, new_note_f]
        ):
            dset = f[name]
            old_shape = dset.shape[0]
            new_shape = old_shape + 1
            dset.resize((new_shape,))
            dset[old_shape:] = new_data

def getDataset(datasetFileName="dataset",isTrainDataset=False):
    with h5py.File(datasetFileName + ".h5", 'r') as f:
        content = [c.decode('utf-8') for c in f['content'][:]]
        link = [c.decode('utf-8') for c in f['link'][:]]
        date = [c.decode('utf-8') for c in f['date'][:]]
        crypto = [c.decode().split(",") for c in f['crypto'][:]]
        note =  f['note'][:]

    if isTrainDataset:
        return content, link, date, crypto, note
    else:
        return content, link, date, crypto

def getArticleDataset(index,datasetFileName="dataset",isTrainDataset=False):
    content, link, date, crypto, note = getDataset(datasetFileName=datasetFileName,isTrainDataset=isTrainDataset)

    content = content[index]
    link = link[index]
    date = date[index]
    crypto = crypto[index]
    note = note[index]

    if isTrainDataset:
        return content, link, date, crypto, note
    else:
        return content, link, date, crypto

def getDatasetLength(datasetFileName="dataset"):
    content, link, date, crypto = getDataset(datasetFileName=datasetFileName)
    return len(content)

def getDatasetPlaceholderAttribute(datasetFileName="dataset"):
    with h5py.File(datasetFileName + ".h5", 'r') as f:
        placeHolderAttribute = f.attrs['placeholderContent']
    return placeHolderAttribute

def setDatasetPlaceholderAttribute(newValue,datasetFileName="dataset"):
    with h5py.File(datasetFileName + ".h5", "r+") as f:
        f.attrs['placeholderContent'] = newValue

def getUrlAttribute(website,datasetFileName="dataset"):
    """
    website_value : str
        'last_news_cryptoNews'
        'last_news_uToday'
        'last_news_beInCrypto'
    """
    with h5py.File(datasetFileName + ".h5", 'r') as f:
        placeHolderAttribute = f.attrs[website]
    return placeHolderAttribute

def setUrlAttribute(website,newValue,datasetFileName="dataset"):
    """
    website_value : str
        'last_news_cryptoNews'
        'last_news_uToday'
        'last_news_beInCrypto'
    """
    with h5py.File(datasetFileName + ".h5", "r+") as f:
        f.attrs[website] = newValue

def updateArticleDataset(index, new_content, new_link, new_date, new_crypto, new_note=None, datasetFileName="dataset", isTrainDataset=False):
    try:
        with h5py.File(datasetFileName + ".h5", 'r+') as f:
            # Strings simples : on encode direct en bytes
            f['content'][index] = new_content.encode('utf-8')
            f['link'][index] = new_link.encode('utf-8')
            f['date'][index] = new_date.encode('utf-8')
            
            # Liste de strings crypto -> string joinée + encodée
            crypto_str = ",".join(new_crypto)
            f['crypto'][index] = crypto_str.encode('utf-8')

            # Note si dataset d'entraînement
            if isTrainDataset and new_note is not None:
                f['note'][index] = new_note

            print(f"Article à l’index {index} mis à jour avec succès.")
    
    except IndexError:
        print("Erreur : index en dehors des limites.")
    except KeyError as e:
        print(f"Erreur : champ manquant dans le dataset ({e}).")
    except Exception as e:
        print(f"Erreur inattendue : {e}")



def readDataset(datasetFileName="dataset"):
    with h5py.File(datasetFileName + ".h5", 'r') as f:
        print("Attributs du fichier HDF5 :")
        for key, value in f.attrs.items():
            print(f"{key}: {value}")

        print("Contenu du fichier HDF5 :")
        print(f.keys())

        print("Number of data : ",len(f['content']))

        content = [c.decode('utf-8') for c in f['content'][:]]
        link = [c.decode('utf-8') for c in f['link'][:]]
        date = [c.decode('utf-8') for c in f['date'][:]]
        crypto = [c.decode().split(",") for c in f['crypto'][:]]
        note =  f['note'][:]

        print("Content : ", content)
        print("Link : ", link)
        print("Date : ",date)
        print("Crypto : ", crypto)
        print("Note : ", note)


if __name__ == "__main__":
    createDataset(["Content"],["url"],["test"],[["List","crypto"]],[0.5], "dataset")
    
    readDataset("dataset")

    

    # FOR DEBUG ONLY
    # appendArticleToDataset(
    #     new_content="Nouvel article",
    #     new_link="https://example.com/article",
    #     new_date="2025-05-20",
    #     new_crypto=["btc"],
    #     new_note=0.0
    # )

    #remove_first_item()

    # updateArticleDataset(
    #     index=0,
    #     new_content="article 0",
    #     new_link="https://example0.com/article",
    #     new_date="2025-05-18",
    #     new_crypto=["Ether"],
    #     new_note=0.92,
    #     isTrainDataset=True
    # )