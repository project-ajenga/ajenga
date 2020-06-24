import asyncio
from typing import NoReturn

from aiocqhttp import Event as CQEvent
from aiocqhttp.message import escape, unescape, Message, MessageSegment

from ajenga import Ajenga, get_bot, Service, get_loaded_services
from ajenga.helpers import join_str
from ajenga.exceptions import *
from ajenga.log import logger
from .preprocessor import MessagePreprocessorSolver, get_preprocessors
from .processor import MessageProcessorSolver


CTX_KEY_SHORT = '_short'


async def handle_message(bot: Ajenga, event: CQEvent) -> None:
    _log_message(event)

    assert isinstance(event.message, Message)
    if not event.message:
        event.message.append(MessageSegment.text(''))  # type: ignore

    # Solve preprocessors
    preprocessors = get_preprocessors()
    presolver = MessagePreprocessorSolver()
    coros = list(presolver.get(preprocessor, bot, event, presolver) for preprocessor in preprocessors)
    if coros:
        future = asyncio.gather(*coros)
        try:
            await future
        except CanceledException:
            future.cancel()
            logger.info(f'Message {event["message_id"]} is ignored')
            return

    short_execution = event.get(CTX_KEY_SHORT, get_bot().config.MESSAGE_HANDLE_SHORT)

    while True:
        try:
            used_processors = dict()
            services = get_loaded_services()
            for service in services:
                if service.check_priv(event):
                    for processor in service.registered_processors:
                        used_processors.setdefault(processor, set())
                        used_processors[processor].add(service)

            solver = MessageProcessorSolver(short_execution)

            # Sequential execution for short handling
            if short_execution:
                handled = False
                for processor in used_processors:
                    try:
                        result = await solver.get(processor, bot, event, solver)
                        if not result:
                            continue
                    except FinishedException as e:
                        if e.success:
                            break
                        else:
                            continue
                    except FailedException as e:
                        continue
                    except Exception as e:
                        logger.exception(e)
                        logger.error(f'Error occurred when process message {event.message_id} by {processor}.')
                        continue

                    ev_name = join_str((processor, event.name))
                    for service in used_processors[processor]:
                        try:
                            handled = await service.handle_event_short(ev_name, *result)
                        except FinishedException as e:
                            if e.success:
                                break
                            else:
                                continue
                        except Exception as e:
                            # Error should be handled by Service, critical
                            logger.exception(e)
                            logger.critical(f'Error occurred when process message {event.message_id}')
                            continue
                        if handled:
                            break
                    if handled:
                        break
            else:
                processors = used_processors.keys()
                coros = list(solver.get(processor, bot, event, solver) for processor in processors)
                results = await asyncio.gather(*coros, return_exceptions=True)

                coros = []
                for processor, result in zip(processors, results):
                    if not result or isinstance(result, FinishedException) or isinstance(result, FailedException):
                        continue
                    elif isinstance(result, SwitchedException):
                        raise result
                    elif isinstance(result, Exception):
                        logger.exception(result)
                        logger.error(f'Error occurred when process message {event.message_id} by {processor}.')
                        continue

                    services = used_processors[processor]
                    ev_name = join_str((processor, event.name))
                    coros.extend(service.handle_event(ev_name, *result) for service in services)

                results = await asyncio.gather(*coros, return_exceptions=True)
                for result in results:
                    if isinstance(result, SwitchedException):
                        raise result
                    elif isinstance(result, Exception):
                        # Error should be handled by Service, critical
                        logger.exception(result)
                        logger.critical(f'Error occurred when process message {event.message_id}')
                        continue
            break
        except SwitchedException as e:
            event['message'] = e.new_message
            event['to_me'] = True


def switch_message(new_message: Message) -> NoReturn:
    raise SwitchedException(new_message)


def finish_message(bot, ctx, *args, **kwargs) -> NoReturn:
    asyncio.run_coroutine_threadsafe(bot.send(ctx, *args, **kwargs), bot.loop)
    raise FinishedException(True)


def _log_message(event: CQEvent) -> None:
    msg_from = str(event.user_id)
    if event.detail_type == 'group':
        msg_from += f'@[群:{event.group_id}]'
    elif event.detail_type == 'discuss':
        msg_from += f'@[讨论组:{event.discuss_id}]'
    logger.info(f'Self: {event.self_id}, '
                f'Message {event.message_id} from {msg_from}: '
                f'{repr(str(event.message))}')
