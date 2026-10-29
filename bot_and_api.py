import os
import json
import threading
from datetime import datetime
from flask import Flask, jsonify
from flask_cors import CORS
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# ⚠️ ضع التوكن الخاص بك هنا
TOKEN = '8804131470:AAGyfcSlTrfhdlyiMQ3vdKMqBNDXegPHeyg'

# ==========================================
# 1. هيكل المنيو
# ==========================================
MENU = {
    "KEBAB": {
        "Kebab Standart pui": 70, "Kebab Mare pui": 80, "New Kebab": 90,
        "Mexicano Kebab": 90, "Crispy Kebab": 90, "Nuggets Kebab": 90,
        "Kebab Standart vită": 75, "Kebab Mare vită": 100, "Kebab fără carne": 60,
        "Vegetarian Kebab": 80,
    },
    "SHAWERMA": {"Shawerma Standart pui": 75, "Shawerma Mare pui": 100},
    "PITA": {"Pita pui": 70, "Pita vită": 80, "Pita crispy": 80},
    "BURGER": {"Burger pui": 80, "Burger crispy": 90, "Burger vită": 85, "Big Burger vită": 130},
    "BAGGETT": {"Baggett pui": 100, "Baggett vită": 120, "Baggett crispy / nuggets": 120},
    "GUSTĂRI": {"Nuggets": 85, "Crispy": 85, "Cartofi pai 200 g": 80},
    "MENIURI": {
        "Menu Kebab Standart pui": 120, "Menu Kebab Mare pui": 130, "Menu Shawerma Standart pui": 125,
        "Menu Shawerma Mare pui": 150, "Menu Kebab Standart vită": 130, "Menu Kebab Mare vită": 160,
        "Menu Kebab crispy / nuggets": 140, "Menu Picant Mexicano / New Kebab": 140,
        "Menu Fast Kebab": 250, "Menu Pita pui": 120, "Menu Pita vită / crispy": 130,
        "Menu Crispy": 130, "Menu Nuggets": 130, "Menu Burger pui": 130,
        "Menu Burger vită / crispy": 140, "Menu Baggett pui": 150, "Menu Baggett vită / crispy": 170,
    },
    "DESERT": {"Baklava 100 g": 60},
    "ADAOSURI": {
        "Carne de pui": 20, "Carne de vită": 30, "Cașcaval": 20,
        "Lavaș": 10, "Ciuperci": 20, "Măsline": 20, "Sos": 15,
    }
}

def get_main_menu_keyboard():
    keyboard = []
    categories = list(MENU.keys())
    for i in range(0, len(categories), 2):
        row = [InlineKeyboardButton(categories[i], callback_data=f"cat_{categories[i]}")]
        if i + 1 < len(categories):
            row.append(InlineKeyboardButton(categories[i+1], callback_data=f"cat_{categories[i+1]}"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🛒 Coșul meu / Моя корзина", callback_data="view_cart")])
    return InlineKeyboardMarkup(keyboard)

def get_cart_total(cart):
    return sum(item['price'] * item['qty'] for item in cart.values())

# ==========================================
# 2. دوال البوت
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['cart'] = {}
    context.user_data['state'] = None
    await update.message.reply_text("🍔 Bine ați venit! / Добро пожаловать!", reply_markup=get_main_menu_keyboard(), parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if 'cart' not in context.user_data: context.user_data['cart'] = {}

    if data.startswith("cat_"):
        category_name = data.replace("cat_", "")
        products = MENU.get(category_name, {})
        keyboard = [[InlineKeyboardButton(f"{p_name} - {p_price} MDL", callback_data=f"add_{category_name}|{p_name}")] for p_name, p_price in products.items()]
        keyboard.append([InlineKeyboardButton("🔙 Înapoi / Назад", callback_data="back_to_menu")])
        await query.edit_message_text(text=f"📋 **{category_name}**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "back_to_menu":
        await query.edit_message_text(text="Alegeți o categorie:", reply_markup=get_main_menu_keyboard())

    elif data.startswith("add_"):
        _, item_data = data.split("_", 1)
        category, product_name = item_data.split("|", 1)
        price = MENU[category][product_name]
        cart = context.user_data['cart']
        if product_name in cart: cart[product_name]['qty'] += 1
        else: cart[product_name] = {'price': price, 'qty': 1}
        await query.answer(f"✅ Adăugat: {product_name}")
        
        keyboard = [[InlineKeyboardButton(f"{p_name} - {p_price} MDL", callback_data=f"add_{category}|{p_name}")] for p_name, p_price in MENU[category].items()]
        keyboard.append([InlineKeyboardButton("🛒 Vezi Coșul / Корзина", callback_data="view_cart")])
        keyboard.append([InlineKeyboardButton("🔙 Înapoi / Назад", callback_data="back_to_menu")])
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "view_cart":
        cart = context.user_data['cart']
        if not cart:
            await query.answer("Coșul este gol!", show_alert=True)
            return
        text = "🛒 **Coșul tău:**\n\n"
        for name, item in cart.items(): text += f"▪️ {item['qty']}x {name} = {item['price'] * item['qty']} MDL\n"
        total = get_cart_total(cart)
        text += f"\n💰 **Total: {total} MDL**"
        keyboard = [
            [InlineKeyboardButton("✅ Finalizează / Оформить", callback_data="checkout")],
            [InlineKeyboardButton("🗑 Golește / Очистить", callback_data="clear_cart")],
            [InlineKeyboardButton("🔙 Înapoi / В меню", callback_data="back_to_menu")]
        ]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "clear_cart":
        context.user_data['cart'] = {}
        await query.answer("🗑 Coșul a fost golit!")
        await query.edit_message_text("Alegeți o categorie:", reply_markup=get_main_menu_keyboard())

    elif data == "checkout":
        context.user_data['state'] = "WAITING_NAME"
        await query.edit_message_text(text="📝 Introduceți **Numele**:\nВведите **Имя**:", parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get('state')
    text = update.message.text
    if state == "WAITING_NAME":
        context.user_data['customer_name'] = text
        context.user_data['state'] = "WAITING_PHONE"
        await update.message.reply_text("📞 Introduceți **Telefonul**:", parse_mode='Markdown')
    elif state == "WAITING_PHONE":
        context.user_data['customer_phone'] = text
        context.user_data['state'] = None
        cart = context.user_data.get('cart', {})
        total = get_cart_total(cart)
        
        order_data = {
            "id": update.message.message_id,
            "date": datetime.now().isoformat(),
            "customer_name": context.user_data.get('customer_name'),
            "customer_phone": context.user_data.get('customer_phone'),
            "order_type": "Takeaway",
            "items": [{"name": k, "qty": v['qty'], "price": v['price']} for k, v in cart.items()],
            "total": total
        }
        try:
            with open("orders.json", "a", encoding="utf-8") as f:
                f.write(json.dumps(order_data, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"Error saving order: {e}")

        context.user_data['cart'] = {}
        await update.message.reply_text(f"✅ Comandă plasată!\nTotal: {total} MDL\nVă așteptăm la restaurant!", reply_markup=get_main_menu_keyboard(), parse_mode='Markdown')

def run_bot():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()

# ==========================================
# 3. خادم Flask API
# ==========================================
app = Flask(__name__)
CORS(app)

@app.route('/get_orders', methods=['GET'])
def get_orders():
    orders_file = 'orders.json'
    orders = []
    if os.path.exists(orders_file):
        with open(orders_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    orders.append(json.loads(line))
    return jsonify(orders)

# تشغيل البوت في الخلفية والخادم في المقدمة
if __name__ == '__main__':
    # تشغيل خادم Flask في الخلفية (Thread)
def run_flask():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    # تشغيل Flask في الخلفية
    threading.Thread(target=run_flask, daemon=True).start()
    # تشغيل البوت في الخيط الرئيسي (لحل مشكلة Python 3.14)
    print("Starting Telegram Bot...")
    run_bot()
