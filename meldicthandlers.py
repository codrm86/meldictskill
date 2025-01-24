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

def format_error(text: str, e: Exception) -> str:
    if Config().debug.enabled:
        debug = "\n".join(tb.format_exception(e))
        max_len = 1024 - len(text)
        debug = debug if len(debug) <= max_len else debug[:max_len]
        text = f"{text}\n{debug}"

    return text

def get_data_key(message: Message) -> str:
    return f"{message.session.session_id}"

def create_response(text: str, tts: str, engine: MelDictEngineAlice, end_session: bool = False) -> AliceResponse:
    hamster_tag = "<speaker effect=\"hamster\">" if engine and engine.hamster else None
    return AliceResponse(
        response=Response(text = text,
                          tts = engine.format_tts(hamster_tag, tts, sep="") if engine else tts,
                          end_session = end_session))

async def get_engine(message: Message, state: FSMContext, force_create: bool = False) -> MelDictEngineAlice:
        engine_key = get_data_key(message)
        engine = None

        if force_create:
            config = Config()
            engine = MelDictEngineAlice(message.skill.id)
            await engine.load_data(config.data.main_csv, config.data.websounds_csv, config.data.tts_csv)
            session_data = await state.update_data({ engine_key: (engine, time.time()) })

            now = time.time()
            remove = list()
            for key, value in session_data.items():
                if key != engine_key and now - value[1] >= 600: # последняя активность 10 минут назад и более
                  remove.append(key)

            with rlock:
                for key in remove:
                    session_data.pop(key)
        else:
            session_data = await state.get_data()
            v = session_data.get(engine_key)
            if v:
                engine = v[0]
                with rlock: session_data[engine_key] = (engine, time.time()) # сброс времени последней активности

        return engine

@dispatcher.message(F.session.new)
async def start_session(message: Message, state: FSMContext) -> AliceResponse:
    text = tts = ""
    engine = None

    try:
        engine = await get_engine(message, state, True)
        text, tts = engine.get_reply()
    except Exception as e:
        logging.error(message.command, exc_info=e)
        text, tts = VoiceMenu().root.something_went_wrong()
        text = format_error(text, e)

    return create_response(text, tts, engine)


@dispatcher.message(F.nlu.intents["menu_open"])
async def menu_message_handler(message: Message, state: FSMContext, engine: MelDictEngineAlice = None) -> AliceResponse:
    text = tts = ""
    engine = None

    try:
        engine = engine if engine else await get_engine(message, state)
        if engine is None: # сообщение пришло без создания сессии
            return await start_session(message, state)

        engine.mode = GameMode.MENU
        text, tts = engine.get_reply()
    except Exception as e:
        logging.error(message.command, exc_info=e)
        text, tts = VoiceMenu().root.something_went_wrong()
        text = format_error(text, e)

    return create_response(text, tts, engine)


@dispatcher.message(F.nlu.intents["menu_select"], F.nlu.intents["menu_select"]["slots"]["mode"]["value"].as_("mode"))
async def mode_message_handler(message: Message, state: FSMContext, mode: str) -> AliceResponse:
    text = tts = ""
    engine = None

    try:
        engine = await get_engine(message, state)
        if engine is None: # сообщение пришло без создания сессии
            return await start_session(message, state)

        if engine.mode == GameMode.MENU:
            if CmdFilter.passed(mode, ("демо", "продемонстрир")):
                engine.mode = GameMode.DEMO
            elif CmdFilter.passed(mode, ("трениро", "потренир")):
                engine.mode = GameMode.TRAIN_MENU
            elif CmdFilter.passed(mode, "экзамен"):
                engine.mode = GameMode.EXAM

        if engine.mode != GameMode.MENU:
            text, tts = engine.get_reply()
        else:
            text, tts = VoiceMenu().root.dont_understand()
    except Exception as e:
        logging.error(message.command, exc_info=e)
        text, tts = VoiceMenu().root.something_went_wrong()
        text = format_error(text, e)

    return create_response(text, tts, engine)


@dispatcher.message(F.nlu.intents["back"])
async def back_message_event_handler(message: Message, state: FSMContext) -> AliceResponse:
    text = tts = ""
    engine = None

    try:
        engine = await get_engine(message, state)
        if engine is None: # сообщение пришло без создания сессии
            return await start_session(message, state)

        match engine.mode:
            case GameMode.MENU:
                text, tts = VoiceMenu().root.no_way_back()
                return create_response(text, tts, engine)
            case GameMode.DEMO | GameMode.TRAIN_MENU | GameMode.EXAM:
                engine.mode = GameMode.MENU
            case GameMode.TRAIN:
                engine.mode = GameMode.TRAIN_MENU
            case _:
                text, tts = VoiceMenu().root.dont_understand()
                return create_response(text, tts, engine)

        text, tts = engine.get_reply()
    except Exception as e:
        logging.error(message.command, exc_info=e)
        text, tts = VoiceMenu().root.something_went_wrong()
        text = format_error(text, e)

    return create_response(text, tts, engine)


@dispatcher.message(F.nlu.intents["stats"])
async def stats_message_handler(message: Message, state: FSMContext) -> AliceResponse:
    text = tts = ""
    engine = None

    try:
        engine = await get_engine(message, state)
        if engine is None: # сообщение пришло без создания сессии
            return await start_session(message, state)

        text, tts = engine.get_stats_reply()
    except Exception as e:
        logging.error(message.command, exc_info=e)
        text, tts = VoiceMenu().root.something_went_wrong()
        text = format_error(text, e)

    return create_response(text, tts, engine)


@dispatcher.message(F.nlu.intents["rules"])
async def stats_message_handler(message: Message, state: FSMContext) -> AliceResponse:
    text = tts = ""
    engine = None

    try:
        engine = await get_engine(message, state)
        if engine is None: # сообщение пришло без создания сессии
            return await start_session(message, state)

        text, tts = engine.get_rules_reply()
    except Exception as e:
        logging.error(message.command, exc_info=e)
        text, tts = VoiceMenu().root.something_went_wrong()
        text = format_error(text, e)

    return create_response(text, tts, engine)


@dispatcher.message(F.nlu.intents["finish"])
async def finish_message_handler(message: Message, state: FSMContext) -> AliceResponse:
    text = tts = ""
    engine = None

    try:
        engine = await get_engine(message, state)
        if engine and engine.mode > GameMode.MENU:
            return await menu_message_handler(message, state, engine=engine)
        
        text, tts = VoiceMenu().root.byebye()
    except Exception as e:
        logging.error(message.command, exc_info=e)
        text, tts = VoiceMenu().root.something_went_wrong()
        text = format_error(text, e)

    return create_response(text, tts, engine, end_session=True)


@dispatcher.message(F.nlu.intents["hamster"]["slots"].not_contains("not"))
async def hamster_handler(message: Message, state: FSMContext) -> AliceResponse:
    text = tts = ""
    engine = None

    try:
        engine = await get_engine(message, state)
        if engine is None: # сообщение пришло без создания сессии
            return await start_session(message, state)

        engine.hamster = True
        text, tts = VoiceMenu().root.hamster_on()
    except Exception as e:
        logging.error(message.command, exc_info=e)
        text, tts = VoiceMenu().root.something_went_wrong()
        text = format_error(text, e)

    return create_response(text, tts, engine)


@dispatcher.message(F.nlu.intents["hamster"]["slots"].contains("not"))
async def not_hamster_handler(message: Message, state: FSMContext) -> AliceResponse:
    text = tts = ""
    engine = None

    try:
        engine = await get_engine(message, state)
        if engine is None: # сообщение пришло без создания сессии
            return await start_session(message, state)

        text, tts = VoiceMenu().root.hamster_off()
        engine.hamster = False
    except Exception as e:
        logging.error(message.command, exc_info=e)
        text, tts = VoiceMenu().root.something_went_wrong()
        text = format_error(text, e)

    return create_response(text, tts, engine)


@dispatcher.message()
async def message_handler(message: Message, state: FSMContext) -> AliceResponse:
    text = tts = ""
    engine = None

    try:
        engine = await get_engine(message, state)
        if engine is None: # сообщение пришло без создания сессии
            return await start_session(message, state)

        repeat = message.nlu.intents.get("YANDEX.REPEAT") is not None or message.nlu.intents.get("repeat") is not None 
        text, tts = engine.process_user_reply(message) if not repeat \
            else engine.get_reply()
    except Exception as e:
        logging.error(message.command, exc_info=e)
        text, tts = VoiceMenu().root.something_went_wrong()
        text = format_error(text, e)

    return create_response(text, tts, engine)