import requests
from bs4 import BeautifulSoup
import pandas as pd

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9"
}

def parse_funpay_structure():
    url = "https://funpay.com"
    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        print("Ошибка доступа к сайту")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    data = []

    game_nodes = soup.find_all('div', class_='promo-game-item')

    for game in game_nodes:
        game_name = game.find('div', class_='game-title').text.strip()

        options = game.find_all('a')
        for option in options:
            opt_name = option.text.strip()
            opt_link = option['href']

            data.append({
                "Game_Name": game_name,
                "Category_Name": opt_name,
                "URL": opt_link,
                "Game_ID": game_name.lower().replace(" ", "_")
            })

    df = pd.DataFrame(data)
    df.to_excel("funpay_games_structure.xlsx", index=False)
    print("Структура успешно сохранена в funpay_games_structure.xlsx")

if __name__ == "__main__":
    parse_funpay_structure()