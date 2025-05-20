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
    crypto = np.array([",".join(c) for c in [["crypto1", "crypto2"], ["crypto3", "crypto4", "crypto5"]]], dtype='S')

    with h5py.File(datasetFileName + ".h5", 'w') as f:
        f.create_dataset('content', data=content, compression="gzip", chunks=True, maxshape=(None,))
        f.create_dataset('link', data=link, compression="gzip", chunks=True, maxshape=(None,))
        f.create_dataset('date', data=date, compression="gzip", chunks=True, maxshape=(None,))
        f.create_dataset('crypto', data=crypto, compression="gzip", chunks=True, maxshape=(None,))
        f.create_dataset('note', data=note, compression="gzip", chunks=True, maxshape=(None,))


        # Optionnel : Ajouter des métadonnées pour mieux organiser
        f.attrs['description'] = 'Dataset d\'articles pour classification'
        f.attrs['source'] = 'Internet'

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


def readDataset(datasetFileName="dataset"):
    with h5py.File(datasetFileName + ".h5", 'r') as f:
        print("Attributs du fichier HDF5 :")
        for key, value in f.attrs.items():
            print(f"{key}: {value}")

        print("Contenu du fichier HDF5 :")
        print(f.keys())

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


createDataset(["Content1","Content2"],["url1","url2"],["test","test2"],[["cypto1","crypto2"],["crypto3","crypto4"]],[0.5,0.8])

readDataset()

appendArticleToDataset(
    new_content="Nouvel article",
    new_link="https://example.com/article",
    new_date="2025-05-20",
    new_crypto=["btc"],
    new_note=0.92
)


readDataset()