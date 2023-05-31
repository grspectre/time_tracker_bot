import psycopg2
from util import config
from dataclasses import dataclass
from typing import Optional, Any, List, Dict
from loguru import logger
import telegram
import json
from datetime import datetime, timezone, timedelta, date, time
from util import get_tags


TIMESTAMP_WITH_TZ = '%Y-%m-%d %H:%M:%S %z'


@dataclass
class User:
    id: int
    user_id: int
    data: dict
    found: bool = False
    table_name: str = 'tt_user'

    def __init__(self, user_id: int) -> None:
        self.load_from_db(user_id)

    def set_data(self, user: telegram.User) -> None:
        user_params = {
            'user_id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_bot': user.is_bot,
            'language_code': user.language_code,
            'username': user.username,
        }
        sql = "INSERT INTO {} (user_id, data) VALUES (%s, %s)".format(self.table_name)
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(sql, (user.id, json.dumps(user_params)))
            conn.commit()
        except (Exception, psycopg2.Error) as error:
            logger.error('PQ error: {}'.format(error))
        finally:
            cursor.close()
            conn.close()

    def load_from_db(self, user_id: int) -> None:
        sql = "SELECT * FROM {} WHERE user_id = %s".format(self.table_name)
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(sql, (user_id,))
            result = cursor.fetchone()
        except (Exception, psycopg2.Error) as error:
            logger.error('PQ error: {}'.format(error))
        finally:
            cursor.close()
            conn.close()
        if result is None:
            return
        self.id, self.user_id, self.data = result
        self.found = True

    def from_data(self, key: str, default_value: Any = None) -> Any:
        if key in self.data:
            return self.data[key]
        return default_value

    def del_from_data(self, key: str) -> None:
        if key in self.data:
            del self.data[key]

    def save(self) -> None:
        sql = "UPDATE {} SET data = %s WHERE id = %s".format(self.table_name)
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(sql, (json.dumps(self.data), self.id))
            conn.commit()
        except (Exception, psycopg2.Error) as error:
            logger.error('PQ error: {}'.format(error))
        finally:
            cursor.close()
            conn.close()

    def set_utc_offset(self, offset: int) -> None:
        self.data['utc_offset'] = offset
        self.save()

    def set_sleep_tag(self, sleep_tag: str) -> None:
        self.data['sleep_tag'] = sleep_tag
        self.save()

    def del_sleep_tag(self) -> None:
        self.del_from_data('sleep_tag')
        self.save()

    def get_utc_offset(self) -> int:
        return self.from_data('utc_offset', 0)

    def get_sleep_tag(self) -> Optional[str]:
        return self.from_data('sleep_tag')


@dataclass
class Message:
    id: int
    tt_user_id: int
    description: str
    data: dict
    event_time: datetime
    message_id: int
    found: bool = False
    table_name: str = 'tt_data'
    summary_tag: str = '#итого'

    def __init__(self, user_id: int,  message_id: int) -> None:
        self.load_from_db(user_id, message_id)

    def set_data(self, message_params: dict) -> None:
        sql = "INSERT INTO {} (tt_user_id, description, data, event_time, message_id) VALUES (%s, %s, %s, %s, %s)".format(self.table_name)
        tt_user_id = message_params['tt_user_id']
        description = message_params['text']
        event_time = message_params['event_time']
        event_time.astimezone(timezone(offset=timedelta(hours=0), name='UTC'))
        message_params['event_time'] = event_time.strftime(TIMESTAMP_WITH_TZ)
        message_id = message_params['message_id']

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(sql, (tt_user_id, description, json.dumps(message_params), event_time, message_id))
            conn.commit()
        except (Exception, psycopg2.Error) as error:
            logger.error('PQ error: {}'.format(error))
        finally:
            cursor.close()
            conn.close()

    def load_from_db(self, user_id: int, message_id: int) -> None:
        sql = """SELECT 
                    id, tt_user_id, description, data, event_time, message_id 
                FROM {} 
                WHERE tt_user_id = %s AND message_id = %s""".format(self.table_name)
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(sql, (user_id, message_id))
            result = cursor.fetchone()
        except (Exception, psycopg2.Error) as error:
            logger.error('PQ error: {}'.format(error))
        finally:
            cursor.close()
            conn.close()
        if result is None:
            return
        self.id, self.tt_user_id, self.description, self.data, self.event_time, self.message_id = result
        self.found = True

    def from_data(self, key: str, default_value: Any = None) -> Any:
        if key in self.data:
            return self.data[key]
        return default_value

    def save(self) -> None:
        sql = "UPDATE {} SET description = %s, data = %s WHERE id = %s".format(self.table_name)
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(sql, (self.description, json.dumps(self.data), self.id))
            conn.commit()
        except (Exception, psycopg2.Error) as error:
            logger.error('PQ error: {}'.format(error))
        finally:
            cursor.close()
            conn.close()

    @classmethod
    def get_stat(cls, user: User, offset: int) -> List:
        rows = cls.get_log(user, offset)
        last_date = None
        output = {
            cls.summary_tag: {
                'seconds': 0,
                'text': []
            }
        }
        for dt, text_item in rows:
            if last_date is None:
                last_date = dt
                continue
            minus = dt - last_date

            text, tags = get_tags(text_item)

            for tag in tags:
                if tag not in output:
                    output[tag] = {
                        'seconds': 0,
                        'texts': [],
                        'texts_seconds': {}
                    }
                if text not in output[tag]['texts']:
                    output[tag]['texts'].append(text)
                if text not in output[tag]['texts_seconds']:
                    output[tag]['texts_seconds'][text] = 0
                output[tag]['seconds'] += minus.total_seconds()
                output[tag]['texts_seconds'][text] += minus.total_seconds()
                output[cls.summary_tag]['seconds'] += minus.total_seconds()
            last_date = dt
        return cls.pretty_print(output)
    
    @classmethod
    def pretty_print(cls, data: Dict) -> str:
        data = {k: v for k, v in sorted(data.items(), key=lambda item: item[1]['seconds'])}

        keys = data.keys()
        max_len = len(max(keys, key=len))

        rows = []
        for tag in data:
            if tag == cls.summary_tag:
                continue
            time_delta = str(timedelta(seconds=data[tag]['seconds']))
            texts = data[tag]['texts']

            texts_formatted = []
            for text in texts:
                secs = data[tag]['texts_seconds'][text]
                text_time_delta = str(timedelta(seconds=secs))
                texts_formatted.append('{} ({})'.format(text, text_time_delta))

            rows.append('{}: {} {}'.format(' '*(max_len-len(tag)) + tag, time_delta, ', '.join(texts_formatted)))

        rows.append('')
        time_delta = str(timedelta(seconds=data[cls.summary_tag]['seconds']))
        rows.append('{}: {} {}'.format(' '*(max_len-len(cls.summary_tag)) + cls.summary_tag, time_delta, ''))
        return '\n'.join(rows)

    @classmethod
    def get_sql_with_sleep_tag(cls, min_date: date, max_date: date, sleep_tag: str, user_id: int) -> tuple:
        template = """SELECT * FROM {table} WHERE tt_user_id = %s
AND event_time BETWEEN
(
  SELECT min(event_time)
  FROM {table}
  WHERE date(event_time) = %s AND data->'tracker_tags' ? %s AND tt_user_id = %s
) AND (
  SELECT CASE WHEN min(event_time) IS NULL THEN now() ELSE min(event_time) END
  FROM {table}
  WHERE date(event_time) > %s AND data->'tracker_tags' ? %s AND tt_user_id = %s
) ORDER BY event_time""".format(table=cls.table_name)
        return (template, (user_id, min_date, sleep_tag, user_id, max_date, sleep_tag, user_id,))

    @classmethod
    def get_default_sql(cls, min_date: date, max_date: date, tzinfo: timezone, user_id: int) -> tuple:
        date1 = datetime.combine(min_date, time(0, 0), tzinfo=tzinfo)
        date2 = datetime.combine(max_date, time(23, 59, 59), tzinfo=tzinfo)
        template = """SELECT event_time, description 
        FROM {table}
        WHERE tt_user_id = %s AND event_time BETWEEN %s AND %s
        ORDER BY event_time""".format(table=cls.table_name)
        return (template, (user_id, date1, date2))

    @classmethod
    def get_log(cls, user: User, offset: int) -> List:
        tzinfo = timezone(timedelta(hours=user.get_utc_offset()))
        d = cls.get_date_by_offset(offset)

        sleep_tag = user.get_sleep_tag()
        if sleep_tag is None:
            sql, params = cls.get_default_sql(d,  d, tzinfo, user.id)
        else:
            sql, params = cls.get_sql_with_sleep_tag(d,  d, sleep_tag, user.id)

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(sql, params)
            result = cursor.fetchall()
        except (Exception, psycopg2.Error) as error:
            logger.error('PQ error: {}'.format(error))
        finally:
            cursor.close()
            conn.close()
        if result is None:
            return []
        return result
    
    @staticmethod
    def get_date_by_offset(offset: int) -> date:
        return date.today() + timedelta(days = offset)


def get_connection():
    db_name = config('db_name')
    db_user = config('db_user')
    db_password = config('db_password')
    db_port = config('db_port')
    dsn = 'postgresql://{}:{}@localhost:{}/{}'.format(db_user, db_password, db_port, db_name)
    try:
        conn = psycopg2.connect(dsn)
    except:
        return None
    return conn


def get_user(telegram_user: telegram.User) -> User:
    user_id = telegram_user.id
    user = User(user_id)
    if user.found == False:
        user.set_data(telegram_user)
        user = User(user_id)
    return user


def get_message(message_params: dict) -> Message:
    tt_user_id = message_params['tt_user_id']
    message_id = message_params['message_id']
    message = Message(tt_user_id, message_id)
    if message.found == False:
        message.set_data(message_params)
        message = Message(tt_user_id, message_id)
    return message
