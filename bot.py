import telebot
import pandas as pd
import re  # برای جستجوی انعطاف‌پذیر
import time  # برای تاخیر در تلاش مجدد
import numpy as np
from scipy.spatial.distance import cosine

# Replace with your bot's actual token
TOKEN = "7854548836:AAEQ_MoIITV5whtmYUCN9JX5sAA0dwljTIs"

bot = telebot.TeleBot(TOKEN)

# Load Excel data
df = pd.read_excel("DataBase.xlsx", engine="openpyxl")



# نرمال‌سازی متن فارسی
def normalize_persian_text(text):
    if not isinstance(text, str):
        return ""
    text = text.strip()
    text = re.sub(r"ي", "ی", text)  # جایگزینی ي عربی با ی فارسی
    text = re.sub(r"ك", "ک", text)  # جایگزینی ك عربی با ک فارسی
    text = re.sub(r"\s+", " ", text)  # حذف فاصله‌های اضافی
    return text

# print(df.columns)


# پیش‌پردازش داده‌ها
def preprocess_column(column):
    return column.fillna("").astype(str).apply(normalize_persian_text)

columns_to_clean = [
    "نام کالا",    
    "قیمت مصرف کننده(ریال)",
    "آدرس عکس",
    "لینک خرید",
]
for col in columns_to_clean:
    df[col] = preprocess_column(df[col])

@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.reply_to(
        message,
        "سلام! من یک ربات جستجوگر هستم. لطفاً چیزی که می‌خواهید جستجو کنید را وارد کنید.",
    )

@bot.message_handler(func=lambda message: True)
def search(message):
    query = normalize_persian_text(message.text.strip())  # نرمال‌سازی ورودی کاربر
    query_words = query.split()  # جدا کردن کلمات ورودی کاربر

    # جستجوی انعطاف‌پذیر
    def flexible_search(df, query_words):
        try:
            return df[
                df.apply(
                    lambda row: any(
                        all(word in cell for word in query_words if word) for cell in row
                    ),
                    axis=1,
                )
            ]
        except Exception as e:
            print(f"Error during search: {e}")
            return pd.DataFrame()

    # اعمال جستجو روی کل دیتا
    results = flexible_search(df, query_words)

    if results.empty:
        bot.reply_to(message, "نتیجه‌ای پیدا نشد.")
    else:
        max_results = 10
        for index, row in results.head(max_results).iterrows():
            response = (
                f"نام کالا: {row['نام کالا']}\n"
                f"قیمت مصرف کننده(ریال): {row['قیمت مصرف کننده(ریال)']}\n"
                f"لینک خرید: {row['لینک خرید']}\n"
            )

            # ارسال عکس در صورت وجود
            if row["آدرس عکس"].startswith("http"):
                bot.send_photo(message.chat.id, row["آدرس عکس"], caption=response)
            else:
                bot.send_message(message.chat.id, response + "\n(عکس موجود نیست)")
                
@bot.message_handler(content_types=['photo'])
def handle_image(message):
    try:
        # دریافت شناسه فایل
        file_info = bot.get_file(message.photo[-1].file_id)  
        
        # دریافت مسیر فایل
        file_path = file_info.file_path
        
        # دانلود فایل
        downloaded_file = bot.download_file(file_path)
        
        # ذخیره فایل محلی
        with open('temp_image.jpg', 'wb') as new_file:
            new_file.write(downloaded_file)
        
        print("تصویر با موفقیت دانلود شد.")

        # مقایسه تصویر ارسال‌شده با تصاویر دیتابیس
        min_similarity = float('inf')
        best_match_product = None

        for index, row in df.iterrows():
            image_path = row['آدرس عکس']
            similarity = compare_images('temp_image.jpg', image_path)

            if similarity < min_similarity:
                min_similarity = similarity
                best_match_product = row

        if best_match_product is not None:
            response = (
                f"نام کالا: {best_match_product['نام کالا']}\n"
                f"قیمت مصرف کننده: {best_match_product['قیمت مصرف کننده']}\n"
                f"لینک خرید: {best_match_product['لینک خرید']}\n"
            )

            # ارسال عکس در صورت وجود
            if best_match_product["آدرس عکس"].startswith("http"):
                bot.send_photo(message.chat.id, best_match_product["آدرس عکس"], caption=response)
            else:
                bot.send_message(message.chat.id, response + "\n(عکس موجود نیست)")
        else:
            bot.reply_to(message, "محصول مشابه پیدا نشد.")

    except Exception as e:
        print(f"خطا در پردازش تصویر: {e}")
        bot.reply_to(message, "مشکلی در پردازش تصویر پیش آمد.")

    # گرفتن عکس
    file_info = bot.get_file(message.photo[-1].file_id)
    file_path = file_info.file_path
    downloaded_file = bot.download_file(file_path)
    
    with open('temp_image.jpg', 'wb') as new_file:
        new_file.write(downloaded_file)
    
    # مقایسه تصویر ارسال‌شده با تصاویر دیتابیس
    min_similarity = float('inf')
    best_match_product = None
    
    for index, row in df.iterrows():
        image_path = row['آدرس عکس']
        similarity = compare_images('temp_image.jpg', image_path)
        
        if similarity < min_similarity:
            min_similarity = similarity
            best_match_product = row
    
    if best_match_product is not None:
        response = (
            f"نام کالا: {best_match_product['نام کالا']}\n"
            f"قیمت مصرف کننده: {best_match_product['قیمت مصرف کننده']}\n"
            f"لینک خرید: {best_match_product['لینک خرید']}\n"
        )
        
        # ارسال عکس در صورت وجود
        if best_match_product["آدرس عکس"].startswith("http"):
            bot.send_photo(message.chat.id, best_match_product["آدرس عکس"], caption=response)
        else:
            bot.send_message(message.chat.id, response + "\n(عکس موجود نیست)")
    else:
        bot.reply_to(message, "محصول مشابه پیدا نشد.")
        

def download_image_from_telegram(image_url):
    try:
        # دریافت شناسه فایل از لینک تلگرام
        file_info = bot.get_file(image_url.split('/')[-1])  # استخراج شناسه فایل از لینک

        # دانلود فایل از تلگرام
        downloaded_file = bot.download_file(file_info.file_path)
        
        # ذخیره فایل محلی
        with open('downloaded_image.jpg', 'wb') as new_file:
            new_file.write(downloaded_file)
        print("تصویر با موفقیت دانلود شد.")
        
    except Exception as e:
        print(f"خطا در دانلود تصویر از تلگرام: {e}")



# حلقه برای ری‌کانکت در صورت قطع شدن
while True:
    try:
        bot.polling()
    except Exception as e:
        print(f"Error: {e}. Reconnecting in 5 seconds...")
        time.sleep(5)  # تاخیر قبل از تلاش مجدد
