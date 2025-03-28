import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchWindowException, WebDriverException
import time

# Setup du navigateur avec undetected-chromedriver
options = uc.ChromeOptions()
options.add_argument("--start-maximized")
options.add_argument('--disable-notifications')
options.add_argument('--disable-popup-blocking')
options.add_argument('--disable-infobars')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--no-sandbox')
options.add_argument('--disable-gpu')
options.add_argument('--disable-extensions')
options.add_argument('--disable-software-rasterizer')
options.add_argument('--ignore-certificate-errors')
options.add_argument('--ignore-ssl-errors')

driver = uc.Chrome(options=options)
wait = WebDriverWait(driver, 15)

def scroll_until_element_found():
    """Fonction pour scroller jusqu'à trouver l'élément posts-listing__item"""
    while True:
        try:
            # Chercher l'élément
            element = driver.find_element(By.CSS_SELECTOR, 'li[data-testid="posts-listing__item"]')
            if element:
                return element
        except:
            # Si l'élément n'est pas trouvé, scroller
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

def get_article_links():
    """Fonction pour obtenir les liens des articles visibles"""
    articles = driver.find_elements(By.CSS_SELECTOR, 'li[data-testid="posts-listing__item"] a[href^="/news/"]')
    return [article.get_attribute('href') for article in articles if article.get_attribute('href')]

def safe_switch_to_window(driver, window_handle):
    """Fonction sécurisée pour basculer vers une fenêtre"""
    try:
        driver.switch_to.window(window_handle)
        return True
    except (NoSuchWindowException, WebDriverException):
        return False

# Aller sur Cointelegraph
driver.get("https://cointelegraph.com/")
time.sleep(3)  # Attendre le chargement initial

# Scroller jusqu'à trouver l'élément
print("Scrolling jusqu'à trouver les articles...")
scroll_until_element_found()
print("Articles trouvés !")

processed_links = set()  # Pour garder une trace des articles déjà traités
article_count = 0

while True:
    # Obtenir les liens des articles visibles
    current_links = get_article_links()
    
    # Traiter chaque article non traité
    for link in current_links:
        if link in processed_links:
            continue
            
        try:
            # Sauvegarder la fenêtre principale
            main_window = driver.current_window_handle
            
            # Ouvrir le lien dans un nouvel onglet
            driver.execute_script(f'window.open("{link}", "_blank");')
            time.sleep(1)
            
            # Basculer vers le nouvel onglet
            new_window = driver.window_handles[-1]
            if not safe_switch_to_window(driver, new_window):
                print(f"Impossible d'ouvrir l'article {link}")
                continue
                
            time.sleep(2)
            
            try:
                # Extraire et afficher le titre
                title_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'h1')))
                print(f"[{article_count + 1}] Titre de l'article : {title_element.text}")
            except Exception as e:
                print(f"Impossible de récupérer le titre de l'article {link}")
            
            # Fermer le nouvel onglet
            try:
                driver.close()
            except:
                pass
            
            # Revenir à la fenêtre principale
            if not safe_switch_to_window(driver, main_window):
                print("Impossible de revenir à la fenêtre principale")
                driver.get("https://cointelegraph.com/")
                time.sleep(2)
                continue
            
            processed_links.add(link)
            article_count += 1
            
            # Scroll après chaque 3 articles
            if article_count % 3 == 0:
                print("Scrolling pour charger plus d'articles...")
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
        except Exception as e:
            print(f"Erreur lors du traitement de l'article {link}")
            # S'assurer de revenir à la fenêtre principale en cas d'erreur
            try:
                if not safe_switch_to_window(driver, main_window):
                    driver.get("https://cointelegraph.com/")
                    time.sleep(2)
            except:
                pass
            continue

driver.quit()