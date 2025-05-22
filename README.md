# PC Price Tracker

Scrapes laptops from comparez-malin using additional model specific filters (that the website doesn't offer), saves to csv file, and sends a daily phone notification.

## Features

- Filters by specific GPU, CPU, price
- CSV with clean, separate fields
- Sends phone daily summary through Telegram:
  - Count today / new since yesterday / new ever
  - Best price today / yesterday / ever
- HTML caching (not really needed but implemented just in case for not spamming the website)

## Usage
Choose `SEARCH_URL` using the website's already provided filters (it's important to already filter here as much as possible on the website to scrap as little pages as possible) 
Choose `TARGET_GPU`, `TARGET_CPU`, `MAX_PRICE`
Set `BOT_TOKEN` and `CHAT_ID` in the script, then add it to cron to run daily

Rquirements:
python3:
  requests
  beautifulsoup4
