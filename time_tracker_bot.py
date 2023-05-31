from util import config, get_tags
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from loguru import logger
from model import get_user, get_message, Message
import os
from datetime import datetime, timezone, timedelta
from tempfile import TemporaryFile


async def set_utc_offset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.split()
    help_text = 'Use /set_utc_offset [INTEGER_OFFSET(-24..24)], for example /set_utc_offset -3.'

    error = None
    try:
        offset = text[1]
    except IndexError:
        error = 'Offset not defined.'

    if error is None:
        try:
            offset = int(offset)
        except ValueError:
            error = 'Offset must be an integer'

    if error is None:
        if offset < -24 or offset > 24:
            error = 'Offset must be in interval -24..24.'

    if error is not None:
        await update.message.reply_text('{} {}'.format(error, help_text))
        return

    from_user = update.effective_user
    db_user = get_user(from_user)
    db_user.set_utc_offset(offset)
    await update.message.reply_text('UTC offset changed to {:d}'.format(offset))


async def set_sleep_tag_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.split()
    help_text = 'Use /set_sleep_tag #SLEEP_TAG, for example /set_sleep_tag #sleep.'

    error = None
    try:
        sleep_tag = text[1].strip()
    except IndexError:
        error = 'Sleep tag not defined.'

    if error is None:
        try:
            if sleep_tag[0] != '#' or len(sleep_tag) == 1:
                error = 'Value must starts with # and length must be greater than 1.'
        except ValueError:
            error = 'Sleep tag not defined.'

    if error is not None:
        await update.message.reply_text('{} {}'.format(error, help_text))
        return

    from_user = update.effective_user
    db_user = get_user(from_user)
    db_user.set_sleep_tag(sleep_tag)
    await update.message.reply_text('Sleep tag set to {:s}'.format(sleep_tag))


async def delete_sleep_tag_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from_user = update.effective_user
    db_user = get_user(from_user)
    sleep_tag = db_user.get_sleep_tag()
    db_user.del_sleep_tag()
    await update.message.reply_text('Sleep tag {:s} deleted'.format(sleep_tag))


async def log_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    def format_date(dt: datetime, offset: int) -> str:
        str_format = '%Y-%m-%d %H:%M:%S'
        tzinfo = timezone(timedelta(hours=offset))
        return dt.astimezone(tzinfo).strftime(str_format)

    text = update.message.text.split()
    help_text = 'Use /log [INTEGER_OFFSET <= 0], default value is 0, for example /log -3 or /log.'

    error = None
    try:
        offset = text[1]
    except IndexError:
        offset = 0

    try:
        offset = int(offset)
    except ValueError:
        error = 'Offset must be an negative integer'

    if error is None:
        if offset > 0:
            offset = 0

    if error is not None:
        await update.message.reply_text('{} {}'.format(error, help_text))
        return

    from_user = update.effective_user
    db_user = get_user(from_user)

    d = Message.get_date_by_offset(offset)
    caption = 'Лог за {}'.format(d.strftime('%d.%m.%Y'))
    dt = datetime.now()
    file_name = 'log_{}.txt'.format(dt.strftime('%Y%m%d_%H%M%S'))

    messages = Message.get_log(db_user, offset=offset)
    messages = ['{:s} {:s}'.format(format_date(i[0], db_user.get_utc_offset()), i[1]) for i in messages]
    with TemporaryFile(encoding='utf8', mode='w+') as fp:
        fp.write('\n'.join(messages))
        fp.seek(0)
        await update.message.reply_document(fp, caption=caption, filename=file_name)


async def stat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.split()
    help_text = 'Use /stat [INTEGER_OFFSET <= 0], default value is 0, for example /stat -3 or /log.'

    error = None
    try:
        offset = text[1]
    except IndexError:
        offset = 0

    try:
        offset = int(offset)
    except ValueError:
        error = 'Offset must be negative integer or 0.'

    if error is None:
        if offset > 0:
            offset = 0

    if error is not None:
        await update.message.reply_text('{} {}'.format(error, help_text))
        return

    from_user = update.effective_user
    db_user = get_user(from_user)

    message = Message.get_stat(db_user, offset)
    import telegram
    await update.message.reply_text("```\n{}\n```".format(message), parse_mode='Markdown')


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from_user = update.effective_user
    logger.info(from_user)
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
    app.add_handler(CommandHandler("set_utc_offset", set_utc_offset_command))
    app.add_handler(CommandHandler("set_sleep_tag", set_sleep_tag_command))
    app.add_handler(CommandHandler("del_sleep_tag", delete_sleep_tag_command))
    app.add_handler(CommandHandler("log", log_command))
    app.add_handler(CommandHandler("stat", stat_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, track_save))

    app.run_polling()


def get_log_path() -> None:
    path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(path, 'logs', 'info_{time:YYYY-MM-DD}.log')


@logger.catch
def main() -> None:
    logger.add(get_log_path(), level="INFO")
    token = config('token')
    bot_init(token)


if __name__ == '__main__':
    main()
