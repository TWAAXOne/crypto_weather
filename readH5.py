import h5py
import numpy as np
from datetime import datetime, timedelta
from dateutil import parser
import pytz

def parse_date_string(date_str):
    """Parser une date string au format 'May 30, 2025 at 07:08 PM GMT+2'"""
    try:
        # Décoder si c'est un bytes object
        if isinstance(date_str, bytes):
            date_str = date_str.decode('utf-8')
        
        # Parser la date avec dateutil
        date = parser.parse(date_str)
        
        # S'assurer que la date a un timezone
        if date.tzinfo is None:
            date = pytz.UTC.localize(date)
        
        return date
    except Exception as e:
        print(f"Erreur lors du parsing de la date: {date_str}, erreur: {e}")
        return None

def analyze_dates_distribution(dates_data, is_timestamp=False):
    """Analyser la distribution des dates par rapport à maintenant"""
    now = datetime.now(pytz.UTC)
    
    print(f"\nDate/heure actuelle (UTC): {now}")
    
    # Convertir en objets datetime selon le format
    if is_timestamp:
        dates = [datetime.fromtimestamp(ts, tz=pytz.UTC) for ts in dates_data]
    else:
        dates = []
        for date_str in dates_data:
            parsed_date = parse_date_string(date_str)
            if parsed_date:
                dates.append(parsed_date)
    
    if not dates:
        print("Aucune date valide trouvée!")
        return
    
    # Trouver les dates min et max
    oldest_date = min(dates)
    newest_date = max(dates)
    print(f"\nPlus ancienne date: {oldest_date}")
    print(f"Plus récente date: {newest_date}")
    print(f"Écart avec maintenant: {now - newest_date}")
    
    # Compter les articles par fenêtre temporelle
    windows = {
        "1 heure": timedelta(hours=1),
        "24 heures": timedelta(hours=24),
        "7 jours": timedelta(days=7),
        "30 jours": timedelta(days=30),
        "90 jours": timedelta(days=90)
    }
    
    print("\nDistribution des articles par fenêtre temporelle:")
    for window_name, delta in windows.items():
        cutoff_time = now - delta
        count = sum(1 for date in dates if date and date > cutoff_time)
        percentage = (count / len(dates) * 100) if dates else 0
        print(f"  {window_name}: {count} articles ({percentage:.2f}%)")
    
    # Afficher les 10 articles les plus récents
    print("\n10 articles les plus récents:")
    sorted_dates = sorted(dates, reverse=True)[:10]
    for i, date in enumerate(sorted_dates, 1):
        time_ago = now - date
        days = time_ago.days
        hours = time_ago.seconds // 3600
        minutes = (time_ago.seconds % 3600) // 60
        print(f"  {i}. {date} (il y a {days}j {hours}h {minutes}m)")

print("="*70)
print("ANALYSE DE dataset.h5")
print("="*70)

with h5py.File('dataset.h5', 'r') as f:
    print("Clés principales:", list(f.keys()))
    
    # Afficher le contenu de chaque dataset
    for key in f.keys():
        print(f"\n{'='*50}")
        print(f"Contenu de {key}:")
        print(f"Shape: {f[key].shape}")
        print(f"Type: {f[key].dtype}")
        
        if key == 'timestamps':
            # Analyse détaillée des timestamps
            timestamps = f[key][:]
            analyze_dates_distribution(timestamps, is_timestamp=True)
        elif key == 'date':
            # Analyse des dates au format string
            dates = f[key][:]
            analyze_dates_distribution(dates, is_timestamp=False)
        else:
            print("Premiers éléments:")
            print(f[key][:5])  # Affiche les 5 premiers éléments

# Vérifier aussi test_dataset.h5
print("\n" + "="*70)
print("ANALYSE DE test_dataset.h5")
print("="*70)

try:
    with h5py.File('test_dataset.h5', 'r') as f:
        print("Clés principales:", list(f.keys()))
        
        # Chercher les timestamps
        if 'timestamps' in f:
            print(f"\nContenu de timestamps:")
            print(f"Shape: {f['timestamps'].shape}")
            print(f"Type: {f['timestamps'].dtype}")
            timestamps = f['timestamps'][:]
            analyze_dates_distribution(timestamps, is_timestamp=True)
        
        # Chercher les dates
        if 'date' in f:
            print(f"\nContenu de date:")
            print(f"Shape: {f['date'].shape}")
            print(f"Type: {f['date'].dtype}")
            dates = f['date'][:]
            analyze_dates_distribution(dates, is_timestamp=False)
except Exception as e:
    print(f"Erreur lors de la lecture de test_dataset.h5: {e}")