from aiocqhttp import Error as CQHttpError
from aiocqhttp import Message


class CanceledException(Exception):
    """
    Raised by message preprocessor indicating that
    the bot should ignore the message
    """

    def __init__(self, reason):
        """
        :param reason: reason to ignore the message
        """
        self.reason = reason


class FinishedException(BaseException):
    """
    Raised by message processor or service processor
    indicating that the message has finished processing
    and should not be delivered further
    """

    def __init__(self, success):
        """
        :param success: success or not
        """
        self.success = success


class FailedException(Exception):
    """
    Raised by message processor indicating that
    the message cannot be handled by this processor
    """

    def __init__(self, reason):
        """
        :param reason: reason
        """
        self.reason = reason


class SwitchedException(BaseException):
    """
    Raised by processor indicating that a new message should
    be processed.

    Since the new message will go through handle_message() again,
    the later function should be notified. So this exception is
    intended to be propagated to handle_message().
    """

    def __init__(self, new_message: Message):
        """
        :param new_message: new message which should be placed in event
        """
        self.new_message = new_message


class RejectedException(Exception):
    """
    Raised by message filter indicating that
    the message is rejected and should be handled
    by inner handler
    """

    def __init__(self, reason: str = ''):
        """
        :param reason: reason
        """
        self.reason = reason
