import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchWindowException, WebDriverException
import time

def run_scraper(max_articles=10):
    # Setup du navigateur avec undetected-chromedriver
    options = uc.ChromeOptions()
    # ✅ Essential for Docker headless compatibility
    options.add_argument("--headless=new")  # This is the new headless mode
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    # ✅ Your original flags, kept intact
    options.add_argument("--start-maximized")
    options.add_argument('--disable-notifications')
    options.add_argument('--disable-popup-blocking')
    options.add_argument('--disable-infobars')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-software-rasterizer')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')

    driver = uc.Chrome(options=options)
    wait = WebDriverWait(driver, 15)

    def scroll_until_element_found():
        while True:
            try:
                element = driver.find_element(By.CSS_SELECTOR, 'li[data-testid="posts-listing__item"]')
                if element:
                    return element
            except:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)

    def get_article_links():
        articles = driver.find_elements(By.CSS_SELECTOR, 'li[data-testid="posts-listing__item"] a[href^="/news/"]')
        return [article.get_attribute('href') for article in articles if article.get_attribute('href')]

    def safe_switch_to_window(driver, window_handle):
        try:
            driver.switch_to.window(window_handle)
            return True
        except (NoSuchWindowException, WebDriverException):
            return False

    # Aller sur Cointelegraph
    driver.get("https://cointelegraph.com/")
    time.sleep(3)
    print("Scrolling jusqu'à trouver les articles...")
    scroll_until_element_found()
    print("Articles trouvés !")

    processed_links = set()
    article_data = []
    article_count = 0

    while len(article_data) < max_articles:
        current_links = get_article_links()

        for link in current_links:
            if link in processed_links or len(article_data) >= max_articles:
                continue

            try:
                main_window = driver.current_window_handle
                driver.execute_script(f'window.open("{link}", "_blank");')
                time.sleep(1)

                new_window = driver.window_handles[-1]
                if not safe_switch_to_window(driver, new_window):
                    print(f"Impossible d'ouvrir l'article {link}")
                    continue

                time.sleep(2)

                try:
                    title_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'h1')))
                    title = title_element.text
                    content_elements = driver.find_elements(By.CSS_SELECTOR, 'p')
                    content = " ".join([p.text for p in content_elements if p.text.strip()])
                    article_data.append({
                        "title": title,
                        "content": content
                    })
                    print(f"[{article_count + 1}] Titre: {title}")
                except Exception:
                    print(f"Impossible de récupérer le contenu de l'article {link}")

                try:
                    driver.close()
                except:
                    pass

                safe_switch_to_window(driver, main_window)
                processed_links.add(link)
                article_count += 1

                if article_count % 3 == 0:
                    print("Scrolling pour charger plus d'articles...")
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)

            except Exception as e:
                print(f"Erreur lors du traitement de l'article {link}: {e}")
                try:
                    if not safe_switch_to_window(driver, main_window):
                        driver.get("https://cointelegraph.com/")
                        time.sleep(2)
                except:
                    pass
                continue

    driver.quit()
    return article_data
