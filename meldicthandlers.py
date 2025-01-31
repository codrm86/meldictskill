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
from aliceio.types import AliceResponse, Message, Response, TextButton
from meldictenginealice import *
from myfilters import *
from myconstants import *

dispatcher = Dispatcher()
rlock = threading.RLock()

def format_error(text: str, e: Exception) -> str:
    if Config().debug.enabled:
        debug = "\n".join(tb.format_exception(e))
        max_len = 1024 - len(text) - 1
        debug = debug if len(debug) <= max_len else debug[:max_len]
        text = f"{text}\n{debug}"

    return text

def create_response(text: str, tts: str, engine: MelDictEngineAlice, end_session: bool = False, buttons: list[TextButton] = None) -> AliceResponse:
    if engine is None:
        return AliceResponse(response=Response(text = text, tts = tts, end_session = end_session))

    buttons = engine.get_buttons()
    if buttons: buttons = buttons if isinstance(buttons, list) else list(buttons)

    return AliceResponse(
        response=Response(text = text,
                          tts = engine.format_tts("<speaker effect=\"hamster\">" if engine.hamster else None, tts, sep=""),
                          end_session = end_session,
                          buttons = buttons))

async def get_engine(skill_id: str, session_id: str, state: FSMContext, force_create: bool = False) -> MelDictEngineAlice:
        engine = None

        if force_create:
            config = Config()
            engine = MelDictEngineAlice(skill_id)
            await engine.load_data(config.data.main_csv, config.data.websounds_csv, config.data.tts_csv)
            session_data = await state.update_data({ session_id: (engine, time.time()) })

            now = time.time()
            remove = list()
            for key, value in session_data.items():
                if key != session_id and now - value[1] >= 600: # последняя активность 10 минут назад и более
                  remove.append(key)

            with rlock:
                for key in remove:
                    session_data.pop(key)
        else:
            session_data = await state.get_data()
            v = session_data.get(session_id)
            if v:
                engine = v[0]
                with rlock: session_data[session_id] = (engine, time.time()) # сброс времени последней активности

        return engine

@dispatcher.message(F.session.new)
async def start_session(message: Message, state: FSMContext) -> AliceResponse:
    text = tts = ""
    engine = None

    try:
        engine = await get_engine(message.skill.id, message.session.session_id, state, True)
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
        engine = engine if engine else await get_engine(message.skill.id, message.session.session_id, state)
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
        engine = await get_engine(message.skill.id, message.session.session_id, state)
        if engine is None: # сообщение пришло без создания сессии
            return await start_session(message, state)

        text, tts = engine.process_user_reply(message, mode)
    except Exception as e:
        logging.error(message.command, exc_info=e)
        text, tts = VoiceMenu().root.something_went_wrong()
        text = format_error(text, e)

    return create_response(text, tts, engine)


@dispatcher.message(F.nlu.intents["back"])
async def back_message_handler(message: Message, state: FSMContext, engine: MelDictEngineAlice = None) -> AliceResponse:
    text = tts = ""
    engine = None

    try:
        engine = engine if engine else await get_engine(message.skill.id, message.session.session_id, state)
        if engine is None: # сообщение пришло без создания сессии
            return await start_session(message, state)

        text, tts = engine.process_back_action()
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
        engine = await get_engine(message.skill.id, message.session.session_id, state)
        if engine is None: # сообщение пришло без создания сессии
            return await start_session(message, state)

        text, tts = engine.get_stats_reply()
    except Exception as e:
        logging.error(message.command, exc_info=e)
        text, tts = VoiceMenu().root.something_went_wrong()
        text = format_error(text, e)

    return create_response(text, tts, engine)


@dispatcher.message(F.nlu.intents["rules"])
async def rules_message_handler(message: Message, state: FSMContext) -> AliceResponse:
    text = tts = ""
    engine = None

    try:
        engine = await get_engine(message.skill.id, message.session.session_id, state)
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
        engine = await get_engine(message.skill.id, message.session.session_id, state)
        if engine and engine.mode > GameMode.MENU:
            return await back_message_handler(message, state, engine=engine)

        text, tts = VoiceMenu().root.byebye()
    except Exception as e:
        logging.error(message.command, exc_info=e)
        text, tts = VoiceMenu().root.something_went_wrong()
        text = format_error(text, e)

    return create_response(text, tts, engine, end_session=True)


@dispatcher.message(F.nlu.intents["hamster"])
async def hamster_handler(message: Message, state: FSMContext) -> AliceResponse:
    text = tts = ""
    engine = None

    try:
        engine = await get_engine(message.skill.id, message.session.session_id, state)
        if engine is None: # сообщение пришло без создания сессии
            return await start_session(message, state)

        slots = message.nlu.intents["hamster"].get("slots")
        engine.hamster = slots.get("not") is None if slots else True
        text, tts = VoiceMenu().root.hamster_on() if engine.hamster else VoiceMenu().root.hamster_off()
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
        engine = await get_engine(message.skill.id, message.session.session_id, state)
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


@dispatcher.button_pressed()
async def button_pressed_handler(button: TextButton, state: FSMContext):
    text = tts = ""
    engine = None

    try:
        engine = await get_engine(button.skill.id, button.session.session_id, state)
        if engine is None: # сообщение пришло без создания сессии
            engine = await get_engine(button.skill.id, button.session.session_id, state, True)
            return engine.get_reply()

        text, tts = engine.process_button_pressed(button)
    except Exception as e:
        logging.error(button.payload, exc_info=e)
        text, tts = VoiceMenu().root.something_went_wrong()
        text = format_error(text, e)

    return create_response(text, tts, engine)