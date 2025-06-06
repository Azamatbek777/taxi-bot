import os
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import nest_asyncio
from geopy.distance import geodesic

nest_asyncio.apply()
TOKEN = os.getenv("TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))

users = {"clients": {}, "drivers": {}}

def generate_markup(buttons):
    return ReplyKeyboardMarkup(buttons, one_time_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [[KeyboardButton("Mijoz"), KeyboardButton("Haydovchi")]]
    reply_markup = generate_markup(buttons)
    await update.message.reply_text("TAXSI XIZMAT botiga xush kelibsiz! Iltimos, rolni tanlang:", reply_markup=reply_markup)

async def register_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    role = 'clients' if update.message.text == "Mijoz" else 'drivers'
    context.user_data["role"] = role
    await update.message.reply_text(
        f"{'Mijoz' if role == 'clients' else 'Haydovchi'} sifatida ro'yxatdan o'tdingiz. Iltimos, telefon raqamingizni yuboring:",
        reply_markup=generate_markup([[KeyboardButton("📞 Telefon raqam yuborish", request_contact=True)]]),
    )

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    role = context.user_data.get("role")
    if role:
        contact = update.message.contact
        users[role][update.message.chat_id] = {"phone": contact.phone_number, "location": None, "request": None}
        await update.message.reply_text(
            "Ma'lumotlaringiz qabul qilindi. Iltimos, lokatsiyangizni yuboring:\nEslatma! Telefoninggizda joylashuv funksiyasini yoqishni unutmang.",
            reply_markup=generate_markup([[KeyboardButton("📍 Lokatsiya yuborish", request_location=True)]]),
        )

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    role = context.user_data.get("role")
    if role:
        location = update.message.location
        user_data = users[role].get(update.message.chat_id)
        if user_data:
            user_data["location"] = (location.latitude, location.longitude)
            await update.message.reply_text("Lokatsiyangiz qabul qilindi.")
            if role == 'clients':
                await create_request_for_client(update)
            else:
                await create_request_for_driver(update)

async def create_request_for_client(update: Update):
    await update.message.reply_text(
        "Sizning xizmat so'rovingiz qabul qilindi. Sizga eng yaqin haydovchilarni topyapmiz.",
        reply_markup=generate_markup([[KeyboardButton("🔄 Yangi haydovchi so'rash")]]),
    )
    await show_nearby_drivers(update)

async def create_request_for_driver(update: Update):
    await update.message.reply_text(
        "Siz haydovchi sifatida xizmatga tayyorsiz. Mijozlarni kutyapmiz.",
        reply_markup=generate_markup([[KeyboardButton("🔄 Yangi mijoz so'rash")]]),
    )
    await show_nearby_clients(update)

async def show_nearby_drivers(update: Update):
    client_location = users['clients'][update.message.chat_id].get("location")
    if client_location:
        nearby_drivers = "\n".join([
            f"Haydovchi: {info['phone']} | Lokatsiya: [Google Maps link](https://www.google.com/maps/search/?api=1&query={info['location'][0]},{info['location'][1]})"
            for info in users['drivers'].values() if info['location'] and distance(client_location, info['location']) < 10
        ])
        if nearby_drivers:
            await update.message.reply_text(f"Yaqin haydovchilar:\n{nearby_drivers}", parse_mode='Markdown')
        else:
            await update.message.reply_text("Hozirda sizga yaqin haydovchilar mavjud emas.")
    else:
        await update.message.reply_text("Sizning lokatsiyangizni olishda xatolik yuz berdi.")

async def show_nearby_clients(update: Update):
    driver_location = users['drivers'][update.message.chat_id].get("location")
    if driver_location:
        nearby_clients = "\n".join([
            f"Mijoz: {info['phone']} | Lokatsiya: [Google Maps link](https://www.google.com/maps/search/?api=1&query={info['location'][0]},{info['location'][1]})"
            for info in users['clients'].values() if info['location'] and distance(driver_location, info['location']) < 10
        ])
        if nearby_clients:
            await update.message.reply_text(f"Yaqin mijozlar:\n{nearby_clients}", parse_mode='Markdown')
        else:
            await update.message.reply_text("Hozirda sizga yaqin mijozlar mavjud emas.")
    else:
        await update.message.reply_text("Sizning lokatsiyangizni olishda xatolik yuz berdi.")

def distance(loc1, loc2):
    return geodesic(loc1, loc2).km

async def send_advertisement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat_id == ADMIN_CHAT_ID:
        message = update.message.text[11:].strip()
        if not message:
            await update.message.reply_text("Reklama matni bo'sh bo'lmasligi kerak. Iltimos, reklama matnini yuboring.")
            return
        sent_to_users = 0
        for group in ['clients', 'drivers']:
            for user_id in users[group]:
                try:
                    await context.bot.send_message(user_id, message)
                    sent_to_users += 1
                except Exception as e:
                    print(f"Foydalanuvchiga reklama yuborishda xatolik: {e}")
        await update.message.reply_text(f"Reklama {sent_to_users} ta foydalanuvchiga yuborildi.")
    else:
        await update.message.reply_text("Siz faqat admin sifatida reklama yuborishingiz mumkin.")

def main():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^Mijoz$|^Haydovchi$"), register_user))
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    application.add_handler(MessageHandler(filters.LOCATION, handle_location))
    application.add_handler(CommandHandler("reklama", send_advertisement))
    application.run_polling(timeout=20)

if __name__ == "__main__":
    main()
