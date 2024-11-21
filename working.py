import asyncio
from telethon import TelegramClient
from telethon.errors import ChatWriteForbiddenError
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import sqlite3
from typing import Optional

# Account credentials
accounts = [
   {'api_id': '22367779', 'api_hash': '084babb6387e8eb2e0344ba093942d05', 'phone_number': '+6283121886880'},
    {'api_id': '28856082', 'api_hash': '65aad3f114c51a17433cc40a603fa19f', 'phone_number': '+27788257305'},
    {'api_id': '24179574', 'api_hash': '805672e9c729e98115bab1abc921a62b', 'phone_number': '+8801994832490'},
   
]

# Wait time between messages
wait_time = 2  # Time in seconds to wait after sending each message

# Global variable to track bot status
is_active = False

# Add this global variable
current_task: Optional[asyncio.Task] = None

def read_messages_from_file(file_path):
    """Read messages from a text file and return a list of messages."""
    with open(file_path, 'r') as file:
        return [line.strip() for line in file if line.strip()]

async def send_messages(client, group_link, messages, wait_time):
    global is_active
    reply_to = None

    for message in messages:
        if not is_active:
            print("Bot stopped, interrupting message sending")
            return

        retries = 5
        for attempt in range(retries):
            try:
                if reply_to:
                    await client.send_message(group_link, message, reply_to=reply_to)
                else:
                    await client.send_message(group_link, message)

                print(f'Message sent to {group_link}: {message}')

                last_message = await client.get_messages(group_link, limit=2)
                if len(last_message) > 1:
                    reply_to = last_message[1].id

                break

            except ChatWriteForbiddenError:
                print(f"Cannot send message to {group_link}: You don't have permission to write in this chat.")
                return
            except sqlite3.OperationalError as e:
                if 'database is locked' in str(e):
                    print("Database is locked, retrying...")
                    await asyncio.sleep(2)
                else:
                    print(f"An error occurred: {e}")
                    return
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                return

        await asyncio.sleep(wait_time)

async def main(group_link):
    global is_active
    messages = read_messages_from_file('messages_account_1.txt')
    clients = []

    try:
        # Initialize clients
        for account in accounts:
            if not is_active:
                raise asyncio.CancelledError("Bot stopped during initialization")
            try:
                client = TelegramClient(f'session_{account["phone_number"]}', account['api_id'], account['api_hash'])
                await client.start()
                clients.append(client)
                print(f"Client {account['phone_number']} connected successfully")
            except Exception as e:
                print(f"Failed to initialize client {account['phone_number']}: {e}")
                continue

        # Send messages using all active clients
        max_messages = len(messages)
        for i in range(max_messages):
            if not is_active:
                raise asyncio.CancelledError("Bot stopped during message sending")

            for client in clients:
                if not is_active:
                    raise asyncio.CancelledError("Bot stopped during message sending")
                if i < len(messages):
                    try:
                        await send_messages(client, group_link, [messages[i]], wait_time)
                        await asyncio.sleep(wait_time)
                    except Exception as e:
                        print(f"Error sending message: {e}")
                        continue

    except asyncio.CancelledError:
        print("Task was cancelled")
        raise
    finally:
        # Cleanup: Disconnect all clients
        for client in clients:
            try:
                await client.disconnect()
            except Exception as e:
                print(f"Error disconnecting client: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_active, current_task
    is_active = True
    current_task = None  # Reset the current task
    await update.message.reply_text('Welcome! Please send the group link you want to use.')

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_active, current_task
    is_active = False
    
    await update.message.reply_text('Stopping all message sending operations. Please wait...')
    
    # Cancel the current task if it exists
    if current_task and not current_task.done():
        current_task.cancel()
        try:
            await current_task
        except asyncio.CancelledError:
            pass
        
    await update.message.reply_text('The bot has been stopped. Send /start to activate it again.')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_active, current_task
    if not is_active:
        await update.message.reply_text('The bot is currently stopped. Send /start to activate it again.')
        return

    group_link = update.message.text.strip()
    
    # Basic validation for group link
    if not (group_link.startswith('https://t.me/') or group_link.startswith('@')):
        await update.message.reply_text('Please provide a valid Telegram group link (https://t.me/... or @...)')
        return

    await update.message.reply_text(f'Group link received: {group_link}. Starting the message sender...')
    
    try:
        # Create a new task instead of awaiting directly
        current_task = asyncio.create_task(main(group_link))
        await update.message.reply_text('Message sending started in background!')
    except Exception as e:
        await update.message.reply_text(f'An error occurred: {str(e)}')

def main_bot():
    # Replace 'YOUR_BOT_TOKEN' with your actual bot token
    application = ApplicationBuilder().token('7603891491:AAFExcWayI-hz28f1Erl-ujJ-qatzlLtLPo').build()

    # Register handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('stop', stop))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main_bot()