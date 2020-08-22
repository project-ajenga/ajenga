import argparse


class ParserExit(Exception):

    def __init__(self, status=0, message=None):
        self.status = status
        self.message = message


class ArgumentParser(argparse.ArgumentParser):

    def exit(self, status=0, message=None):
        raise ParserExit(status=status, message=message)
