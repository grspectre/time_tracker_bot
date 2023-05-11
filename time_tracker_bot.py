from util import config, get_tags
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from loguru import logger
from model import get_user, get_message, Message
from datetime import datetime, timezone, timedelta


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from_user = update.effective_user
    logger.info(from_user)
    db_user = get_user(from_user)
    await update.message.reply_text("Hello, it is a time tracker bot. Just type something with tag #, for example #wake_up or time tracker #mini_project. For additional help use /help")


async def track_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from_user = update.effective_user
    db_user = get_user(from_user)

    is_edited = False
    if update.edited_message is None:
        text = update.message.text
        [title, tags] = get_tags(text)
        event_time = update.message.date

        params = {
            'message_id': update.message.message_id,
            'chat_id': update.message.chat_id,
            'text': text,
            'tracker_title': title,
            'tracker_tags': tags,
            'bot_message_id': None,
            'tt_user_id': db_user.id,
            'user_id': db_user.user_id,
            'event_time': event_time,
        }

        db_message = get_message(params)
    else:
        is_edited = True
        db_message = Message(db_user.id, update.edited_message.message_id)
        text = update.edited_message.text
        [title, tags] = get_tags(text)

    data = db_message.data
    data['text'] = text
    data['tracker_tags'] = tags
    data['tracker_title'] = title
    db_message.description = text

    if not is_edited:
        message = await update.message.reply_text('⛭ ' + db_message.description)
        data['bot_message_id'] = message.message_id
    else:
        bot_message_id = db_message.from_data('bot_message_id')
        chat_id = db_message.from_data('chat_id')
        logger.info(bot_message_id)
        logger.info(chat_id)
        await context.bot.editMessageText('⛭ ' +  db_message.description, message_id=bot_message_id, chat_id=chat_id)
    db_message.data = data
    db_message.save()


async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'Hello {update.effective_user.first_name}')


def bot_init(token: str) -> None:
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("hello", hello))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, track_save))

    app.run_polling()


@logger.catch
def main() -> None:
    logger.add('logs/info_{time:YYYY-MM-DD}.log', level="INFO")
    token = config('token')
    bot_init(token)


if __name__ == '__main__':
    main()
