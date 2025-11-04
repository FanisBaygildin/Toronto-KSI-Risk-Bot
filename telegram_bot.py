# telegram_bot0.py
from telegram import Update
from telegram.ext import (
                        ApplicationBuilder,
                        CommandHandler,
                        MessageHandler,
                        ConversationHandler,
                        ContextTypes,
                        filters,
                        Application,
                        )
import os
from google_maps_route import get_routes, static_map
from weather_api import build_weather_row, weather_df_for_route
import joblib, numpy as np
from pathlib import Path
import asyncio
from telegram.ext import PicklePersistence
import logging
import re



# --- states ---------------------------------------------------------
AUTH_STATE, START_STATE, DESTINATION_STATE = range(3)    # current dialog state
MAX_TRIES = 5



# --- /AUTHORIZATION -------------------------------------------------
'''
The functon handles the password check part:
compares the entered pwd with the real one
If the pwd is correct:
    user is marked as authorizationd (auth=True)
    failed-attempt counter is cleared
    the bot asks for the starting postal code and moves to the START_STATE state
If the pwd is wrong:
    if the user reaches the MAX_TRIES, the conversation ends, effectively locking them out
    else the number of failed attempts (auth_tries) is increased showing how many attempts they’ve used...
'''
async def authorization(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if context.user_data.get("auth"):
        await update.message.reply_text("📍 Please send the start point postal code. \nE.g. M6S5A2")
        return START_STATE

    # If not, staying in the AUTH_STATE
    if "auth_tries" not in context.user_data:
        context.user_data["auth_tries"] = 0
        await update.message.reply_text("🔒 Enter access password")
        return AUTH_STATE
    
    pwd = update.message.text.strip()
    real = os.getenv("BOT_PASS", "")     # getting the correct pwd; if doesn't exist return ""

    if not real:
        await update.message.reply_text("⚠️ Internal error: the bot pwd not found on the server!")
        return ConversationHandler.END

    if pwd == real:                                  # not elif as these are 2 independent verifications
        context.user_data["auth"] = True             # set the user's key 'auth' = True in the dict
        context.user_data.pop("auth_tries", None)    # failed-attempt counter is cleared by removing the key 'auth_tries'
        await update.message.reply_text("📍 Please send the start point postal code. \nE.g. M6S5A2")
        return START_STATE    # this tells the ConversationHandler to move to the 'start postal code' part

    tries = context.user_data.get("auth_tries", 0) + 1    # number of failed attempts for the user
    context.user_data["auth_tries"] = tries               # assign the new value for the user

    if tries >= MAX_TRIES:    # the user will be locked until Render gets restart
        await update.message.reply_text("⛔ Wrong password! \nYou are locked until the next 'cycle'!")
        return ConversationHandler.END

    await update.message.reply_text(f"❌ Wrong password! (tries: {tries}/{MAX_TRIES}).")
    return AUTH_STATE


# --- POSTAL CODE FORMAT CHECK ---------------------------------------
def validate_postal_code(text: str) -> str | None:
    if not text:
        return None
    code = text.replace(" ", "").upper()
    if re.fullmatch(r"[A-Z]\d[A-Z]\d[A-Z]\d", code):
        return code
    return None


INVALID_PC = "❌ Invalid postal code format! \nExpected format: LNLNLN \nE.g. M4R1R3"


# --- RECEIVE START PC -----------------------------------------------
async def receive_start_pc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    start_pc = validate_postal_code(update.message.text)

    if not start_pc:
        await update.message.reply_text(INVALID_PC)
        return START_STATE

    context.user_data["start_pc"] = start_pc
    
    await update.message.reply_text("📍 Now send the destination point postal code. \nE.g. M4R1R3")
    return DESTINATION_STATE



# --- RECEIVE DESTINATION PC -----------------------------------------
async def receive_dest_pc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    dest_pc = validate_postal_code(update.message.text)

    if not dest_pc:
        await update.message.reply_text(INVALID_PC)
        return DESTINATION_STATE

    context.user_data["dest_pc"] = dest_pc
    
    await update.message.reply_text("⏳ Calculating routes…")

    '''
    Giving start_pc and dest_pc to google_maps_route.py -> get_routes
    getting list of dicts with:
    {
    "distance_km":  round(leg["distance"]["value"] / 1000, 1),
    "duration_text": leg["duration"]["text"],
    "poly":          poly,
    "geohash5":      hashes,
    }
        '''
    try:
        routes = await get_routes(context.user_data["start_pc"], context.user_data["dest_pc"])
    except Exception as e:
        await update.message.reply_text(f"❌ Google Maps error: \n{e}")
        return ConversationHandler.END

    if not routes:
        await update.message.reply_text("❗ No route found")
        return ConversationHandler.END

    # Current Weather from weather_api.py -> build_weather_row
    weather = None    # we expect a call to build_weather_row() to return a dict, but just in case - None
    try:
        weather = await asyncio.to_thread(build_weather_row)    # DF with weather details 
    except Exception as e:
        logging.warning("build_weather_row failed: %s", e)

    # Getting features and built a DF for each route
    # Even if one of the DFs crashes, we don't lose the rest
    dfs = []    # list for a DF per 1 route with weather details
    for idx, r in enumerate(routes, start=1):    # idx starts from 1 for routes numbering
        try:
            df = await asyncio.to_thread(weather_df_for_route, r["geohash5"])
            dfs.append(df)
        except Exception as e:
            logging.warning("weather_df_for_route failed for route: \n%d: %s", idx, e)
            dfs.append(None)    # "failed to collect features" marker for this route

    # ------ KSI-model ------------------------------------------------
    try:
        model_path = Path(__file__).resolve().parent / "model" / "model.pkl"
        model = joblib.load(model_path)
    except Exception as e:
        await update.message.reply_text(f"❌ Model load error: \n{e}")
        return ConversationHandler.END

    # Calculating risk for each route. If df=None/empty for the route, set score=None.
    pairs = []  # список (route_dict, score_or_None)
    for idx, (r, df) in enumerate(zip(routes, dfs), start=1):
        score = None
        try:
            if df is not None and getattr(df, "empty", False) is False:
                # score = float(model.predict_sum(df))
                score = float(model.predict_proba(df)[:, 1].sum())
            else:
                logging.warning("Route %d: empty/None DF -> score=None", idx)
        except Exception as e:
            logging.warning("predict_sum failed for route %d: %s", idx, e)
        pairs.append((r, score))

    logging.info("routes=%d; dfs=%d; scored=%d",
                 len(routes), len(dfs), sum(1 for _, s in pairs if s is not None))

    # ------ Making the return ----------------------------------------
    if weather is not None:
        weather_str = (
            f"Temperature: {weather.get('temp_c','?')} °C,\n"
            f"Humidity: {weather.get('humidity','?')} %,\n"
            f"Wind: {weather.get('wind_kph','?')} km/h,\n"
            f"Dewpoint_c: {weather.get('dewpoint_c','?')} °C,\n"
            f"Visibility: {weather.get('vis_km','?')} km,\n"
            f"Pressure: {weather.get('pressure_mb','?')} mBar\n"
        )
        caption_lines = [f"According to the current weather conditions:\n{weather_str}",
                         "KSI probability per a route is as follows:"
                        ]
    else:
        caption_lines = ["Current Weather: unavailable"]

    # output up to N routes
    COLOR_NAMES = ["Red", "Green", "Blue"]
    for idx, (r, score) in enumerate(pairs, start=1):
        color_name = COLOR_NAMES[idx - 1]
        prob_line = (
            f"{score*100:.3f} %" if isinstance(score, (int, float)) else "n/a"
        )

        caption_lines += [
            f"Route {idx} ({color_name} Line, {r.get('distance_km','?')} km): {prob_line}"
            ]
  
    caption = "\n".join(caption_lines)

    # Trying to get a static map (even if score=None for some routes)
    try:
        img_bytes = await static_map(
            context.user_data["start_pc"],
            dest_pc,
            [r["poly"] for r, _ in pairs if "poly" in r],
        )
        await update.message.reply_photo(photo=img_bytes, caption=caption)
    except Exception as e:
        await update.message.reply_text(caption + f"\n(карту показать не удалось: {e})")

    return ConversationHandler.END


# --- ECHO ------------------------------------------------------------
async def echo_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text((update.message.text or "").strip())



# --- APPLICATION BUILD -----------------------------------------------
'''
This function is called from the main.py
Receives Telegram bot token
Returns an object of the calss Application of python-telegram-bot library
app - an object of the bot which is ready for handlers adding
conv - a conversation handler always starting with start func, 
        and then depending on the current state of the dialog

'''

def build_application(token: str) -> Application:
    app = ApplicationBuilder().token(token).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", authorization)],    # this func will be issued when a user sends '/start'
        states = {
            AUTH_STATE:     [MessageHandler(filters.TEXT & ~filters.COMMAND, authorization)],
            START_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_start_pc)],
            DESTINATION_STATE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_dest_pc)]
        }
,
        
        # Handling “emergency” situations
        # fallbacks — a list of handlers that are called if the user has sent something unexpected or wants to exit the dialog
        # the list is empty here, meaning there are no fallback handlers yet
                            
        fallbacks=[],
    )
    app.add_handler(conv)
    return app
