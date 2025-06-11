"""
Module pour parser correctement les dates depuis différentes sources.
Gère les formats ambigus et assure une cohérence dans le parsing.
"""

import re
from datetime import datetime, timedelta
from dateutil import parser as dateutil_parser
import pytz

def parse_date_with_context(date_str, source_url=None):
    """
    Parse une date en tenant compte du contexte (source du site).
    
    Args:
        date_str: La chaîne de date à parser
        source_url: L'URL source pour déterminer le format attendu
    
    Returns:
        str: Date formatée de manière non ambiguë (ISO format avec timezone)
    """
    if isinstance(date_str, bytes):
        date_str = date_str.decode('utf-8')
    
    # Identifier la source
    is_utoday = source_url and 'u.today' in source_url.lower()
    
    # Pattern pour U.Today: "Mon, 9/06/2025 - 6:16"
    utoday_pattern = r'(\w+),\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*-\s*(\d{1,2}):(\d{2})'
    match = re.match(utoday_pattern, date_str)
    
    if match and is_utoday:
        day_name, first_num, second_num, year, hour, minute = match.groups()
        
        # Pour U.Today, le format semble être DD/MM/YYYY
        day = int(first_num)
        month = int(second_num)
        
        # Créer un objet datetime
        dt = datetime(int(year), month, day, int(hour), int(minute))
        
        # Ajouter timezone UTC par défaut
        dt = pytz.UTC.localize(dt)
        
        # Retourner au format ISO pour éviter toute ambiguïté
        return dt.isoformat()
    
    # Pattern pour crypto.news: "Jun 10, 2025 at 02:59 PM GMT+2"
    cryptonews_pattern = r'(\w+)\s+(\d{1,2}),\s+(\d{4})\s+at\s+(\d{1,2}):(\d{2})\s+(AM|PM)\s+(GMT[+-]\d+)?'
    match = re.match(cryptonews_pattern, date_str)
    
    if match:
        month_name, day, year, hour, minute, ampm, timezone = match.groups()
        
        # Convertir le nom du mois en numéro
        months = {
            'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
            'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
        }
        month = months.get(month_name, 1)
        
        # Convertir l'heure en 24h
        hour = int(hour)
        if ampm == 'PM' and hour != 12:
            hour += 12
        elif ampm == 'AM' and hour == 12:
            hour = 0
        
        # Créer datetime
        dt = datetime(int(year), month, int(day), hour, int(minute))
        
        # Gérer le timezone
        if timezone:
            offset_match = re.search(r'GMT([+-])(\d+)', timezone)
            if offset_match:
                sign = offset_match.group(1)
                hours_offset = int(offset_match.group(2))
                if sign == '-':
                    hours_offset = -hours_offset
                
                # Créer un timezone avec l'offset
                tz = pytz.FixedOffset(hours_offset * 60)
                dt = tz.localize(dt)
        else:
            dt = pytz.UTC.localize(dt)
        
        return dt.isoformat()
    
    # Fallback: utiliser dateutil mais avec des indices
    try:
        # Si on a une date ambiguë comme "6/9/2025", essayer de deviner
        if re.search(r'^\d{1,2}/\d{1,2}/\d{4}', date_str):
            # Essayer d'abord en format jour/mois/année (européen)
            try:
                dt = dateutil_parser.parse(date_str, dayfirst=True)
            except:
                # Sinon essayer mois/jour/année (américain)
                dt = dateutil_parser.parse(date_str, dayfirst=False)
        else:
            # Parser normal pour les autres formats
            dt = dateutil_parser.parse(date_str)
        
        # S'assurer qu'on a un timezone
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)
        
        return dt.isoformat()
    
    except Exception as e:
        # En cas d'échec, retourner la date originale
        print(f"Impossible de parser la date: {date_str}, erreur: {e}")
        return date_str

def standardize_date_format(date_str):
    """
    Prend une date sous n'importe quel format et retourne un format standard.
    Format de sortie: "YYYY-MM-DD HH:MM:SS+00:00"
    """
    if isinstance(date_str, bytes):
        date_str = date_str.decode('utf-8')
    
    try:
        # Parser la date ISO si elle est déjà dans ce format
        if 'T' in date_str and ('+' in date_str or 'Z' in date_str):
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        else:
            # Sinon utiliser dateutil
            dt = dateutil_parser.parse(date_str)
        
        # S'assurer qu'on a un timezone
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)
        
        # Convertir en UTC
        dt_utc = dt.astimezone(pytz.UTC)
        
        # Retourner au format standard
        return dt_utc.strftime("%Y-%m-%d %H:%M:%S%z")
    
    except Exception:
        return date_str

if __name__ == "__main__":
    # Tests
    test_dates = [
        ("Jun 10, 2025 at 02:59 PM GMT+2", "https://crypto.news/example"),
        ("Mon, 9/06/2025 - 6:16", "https://u.today/example"),
        ("2025-06-10T14:59:00+02:00", None),
        ("10/06/2025", None),
        ("May 30, 2025 at 07:08 PM GMT+2", "https://crypto.news/example")
    ]
    
    print("Tests de parsing de dates:")
    for date_str, url in test_dates:
        parsed = parse_date_with_context(date_str, url)
        standard = standardize_date_format(parsed)
        print(f"\nOriginal: {date_str}")
        print(f"Parsed:   {parsed}")
        print(f"Standard: {standard}")