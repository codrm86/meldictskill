import threading
import logging
import time
import traceback as tb
from config import Config
from types import SimpleNamespace as dynamic
from aliceio import Dispatcher, Skill, Router, F
from aliceio.exceptions import *
from aliceio.fsm.context import FSMContext
from aliceio.fsm.state import State, StatesGroup
from aliceio.types import AliceResponse, Message, Response, FSInputFile
from meldictenginealice import *
from myfilters import *
from myconstants import *

dispatcher = Dispatcher()
rlock = threading.RLock()

def get_data_key(message: Message) -> str:
    return f"{message.session.session_id}"

async def get_engine(message: Message, state: FSMContext, force_create: bool = False) -> MelDictEngineAlice:
        data = await state.get_data()
        engine_key = get_data_key(message)
        engine = None

        if force_create:
            config = Config()
            engine = MelDictEngineAlice(message.skill.id)
            await engine.load_data(config.data.main_csv, config.data.websounds_csv)
            data = await state.update_data({ engine_key: (engine, time.time()) })

            now = time.time()
            remove = list()
            for key, value in data.items():
                if key != engine_key and now - value[1] >= 600: # последняя активность 10 минут назад и более
                  remove.append(key)

            with rlock:
                for key in remove:
                    data.pop(key)
        else:
            v = data.get(engine_key)
            if v:
                engine = v[0]
                with rlock: data[engine_key] = (engine, time.time()) # сброс времени последней активности

        return engine

def format_error(text: str, e: Exception) -> str:
    return text if not Config().debug.enabled \
        else f"{text}\n\n#DEBUG\n\n{tb.format_exception(e)}"

@dispatcher.message(F.session.new)
async def start_session(message: Message, state: FSMContext) -> AliceResponse:
    text = tts = ""
    try:
        engine = await get_engine(message, state, True)
        text, tts = engine.get_reply()
    except Exception as e:
        logging.error(message.command, exc_info=e)
        tts = AliceReplies.SOMETHING_WENT_WRONG
        text = format_error(tts, e)

    return AliceResponse(response=Response(text=text, tts=tts))


@dispatcher.message(CmdFilter(("меню", "перезапус"), exclude="нет"))
async def menu_message_handler(message: Message, state: FSMContext, engine: MelDictEngineAlice = None) -> AliceResponse:
    text = tts = ""
    try:
        engine = engine if engine else await get_engine(message, state)
        if engine is None: # сообщение пришло без создания сессии
            return await start_session(message, state)

        engine.mode = GameMode.MENU # engine.reset()
        text, tts = engine.get_reply()
    except Exception as e:
        logging.error(message.command, exc_info=e)
        tts = AliceReplies.SOMETHING_WENT_WRONG
        text = format_error(tts, e)

    return AliceResponse(response=Response(text=text, tts=tts))


@dispatcher.message(CmdFilter(("статист", "балл", "оценк"), exclude="нет"))
async def stats_message_handler(message: Message, state: FSMContext) -> AliceResponse:
    text = tts = ""
    try:
        engine = await get_engine(message, state)
        if engine is None: # сообщение пришло без создания сессии
            return await start_session(message, state)

        text, tts = engine.get_stats_reply()
    except Exception as e:
        logging.error(message.command, exc_info=e)
        tts = AliceReplies.SOMETHING_WENT_WRONG
        text = format_error(tts, e)

    return AliceResponse(response=Response(text=text, tts=tts))


@dispatcher.message(CmdFilter(("конец", "закончи", "заканчивай", "выход", "стоп", "останови"), exclude="нет"))
async def end_message_handler(message: Message, state: FSMContext) -> AliceResponse:
    text = tts = ""
    try:
        engine = await get_engine(message, state)
        if engine and engine.mode == GameMode.TASK:
            return await menu_message_handler(message, state, engine=engine)
        
        text = tts = AliceReplies.BYEBYE
    except Exception as e:
        logging.error(message.command, exc_info=e)
        tts = AliceReplies.SOMETHING_WENT_WRONG
        text = format_error(tts, e)

    return AliceResponse(response=Response(text=text, tts=tts, end_session=True))


@dispatcher.message()
async def message_handler(message: Message, state: FSMContext) -> AliceResponse:
    text = tts = ""

    try:
        engine = await get_engine(message, state)
        if engine is None: # сообщение пришло без создания сессии
            return await start_session(message, state)

        text, tts = engine.process_user_reply(message)
        if text is None: text, tts = engine.get_reply()
    except Exception as e:
        logging.error(message.command, exc_info=e)
        tts = AliceReplies.SOMETHING_WENT_WRONG
        text = format_error(tts, e)

    return AliceResponse(response=Response(text=text, tts=tts))