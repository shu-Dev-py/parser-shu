import httpx
import asyncio
import time
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
}

async def fetch_url(client, url):
    response = await client.get(url, headers=headers)

    soup = BeautifulSoup(response.text, "lxml")
    names = soup.find_all("div", class_="tc-desc-text")
    prices = soup.find_all("div", class_="tc-price")
    return names, prices

sr=0


async def main():
    url="https://funpay.com/lots/461/"
    global sr
    valid_items_count = 0
    all_slot = []

    async with httpx.AsyncClient() as client:
        names, prices = await fetch_url(client,url)
        for i, (name, price) in enumerate(zip(names, prices), 1):
            try:
                raw_price = price.text.strip()

                chist_price = raw_price.replace('₽', '').replace(' ', '').split('.')[0]
                price_num=int(chist_price)

                sr += price_num
                valid_items_count += 1
                all_slot.append({
                    "num": i,
                    "name": name.text.strip(),
                    "price": price_num
                })

                print(f"№{i} цена: {price_num } / название:{name.text.strip()}")

            except (ValueError, IndexError):
                continue
        if valid_items_count > 0:
            avg_price = sr // valid_items_count
            sorted_lots = sorted(all_slot, key=lambda x: x['price'])

            print("-" * 30)
            print(f"средняя цена товаров = {avg_price}₽")
            print(f"цена всех товаров = {sr}₽")
            print("-" * 30)
            print(f"5 самых горячих товавров:")

            lot_num=0

            for lot in sorted_lots[:5]:
                lot_num+=1

                print(f"№{lot_num} Цена: {lot['price']}₽ | {lot['name']}")
        else:
            print("товаров не найдено!!!")
if __name__ == "__main__":
    asyncio.run(main())

