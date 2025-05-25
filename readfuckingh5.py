import h5py

with h5py.File('dataset.h5', 'r') as f:
    print("Clés principales:", list(f.keys()))
    
    # Afficher le contenu de chaque dataset
    for key in f.keys():
        print(f"\nContenu de {key}:")
        print(f"Shape: {f[key].shape}")
        print(f"Type: {f[key].dtype}")
        print("Premiers éléments:")
        print(f[key][:5])  # Affiche les 5 premiers éléments