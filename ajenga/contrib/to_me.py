import re
from typing import Iterable

from aiocqhttp import Event as CQEvent
from aiocqhttp.message import MessageSegment

from ajenga import Ajenga, message_preprocessor, MessagePreprocessorSolver
from ajenga.log import logger
from ajenga.exceptions import RejectedException


def _check_at_me(bot: Ajenga, event: CQEvent) -> None:
    if event.detail_type == 'private':
        event['to_me'] = True
    else:
        # group or discuss
        event['to_me'] = False
        at_me_seg = MessageSegment.at(event.self_id)

        # check the first segment
        first_msg_seg = event.message[0]
        if first_msg_seg == at_me_seg:
            event['to_me'] = True
            del event.message[0]

        if not event['to_me']:
            # check the last segment
            i = -1
            last_msg_seg = event.message[i]
            if last_msg_seg.type == 'text' and \
                    not last_msg_seg.data['text'].strip() and \
                    len(event.message) >= 2:
                i -= 1
                last_msg_seg = event.message[i]

            if last_msg_seg == at_me_seg:
                event['to_me'] = True
                del event.message[i:]

        if not event.message:
            event.message.append(MessageSegment.text(''))


def _check_calling_me_nickname(bot: Ajenga, event: CQEvent) -> None:
    first_msg_seg = event.message[0]
    if first_msg_seg.type != 'text':
        return

    first_text = first_msg_seg.data['text']

    if bot.config.NICKNAME:
        # check if the user is calling me with my nickname
        if isinstance(bot.config.NICKNAME, str) or \
                not isinstance(bot.config.NICKNAME, Iterable):
            nicknames = (bot.config.NICKNAME,)
        else:
            nicknames = filter(lambda n: n, bot.config.NICKNAME)
        nickname_regex = '|'.join(nicknames)
        m = re.search(rf'^({nickname_regex})([\s,，]*|$)', first_text,
                      re.IGNORECASE)
        if m:
            nickname = m.group(1)
            logger.debug(f'User is calling me {nickname}')
            event['to_me'] = True
            first_msg_seg.data['text'] = first_text[m.end():]


@message_preprocessor('to_me')
async def _to_me(bot: Ajenga, event: CQEvent, solver: MessagePreprocessorSolver):
    raw_to_me = event.get('to_me', False)
    _check_at_me(bot, event)
    _check_calling_me_nickname(bot, event)
    event['to_me'] = raw_to_me or event['to_me']


async def filter_to_me(bot, ctx, *args):
    if ctx['to_me']:
        return bot, ctx, *args
    else:
        raise RejectedException()
