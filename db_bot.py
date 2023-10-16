from aiogram import Bot, types
import pandas as pd
from aiogram.dispatcher.filters import BoundFilter
from uuid import uuid4

import random
from aiogram.dispatcher.filters.state import StatesGroup, State
import datetime


class Session(StatesGroup):
    restore = State()


class Greeting(StatesGroup):
    done = State()


class Register(StatesGroup):
    token = State()
    team_name = State()


class Quiz(StatesGroup):
    start = State()


class AdminFilter(BoundFilter):
    key = 'admin'

    async def check(self, message: types.Message):
        return message.from_user.id in message.bot.admins


class TeamFinish(BoundFilter):
    key = 'head'

    async def check(self, message: types.Message):
        return message.bot.finish(message.from_user.id)


class TeamHead(BoundFilter):
    key = 'head'

    async def check(self, message: types.Message):
        return message.from_user.id in message.bot.df.columns


class DBBot(Bot):
    def __init__(self, admins, event_number, *args, spec_event_num=0, use_backup=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.admins = admins
        self.event_number = event_number
        self.spec_event_num = spec_event_num
        self.continue_backup = False
        self.current_event = {}
        if use_backup:
            self.df = pd.read_excel("results.xlsx", index_col=0)
            for _id in self.df:
                curr = self._calc_current_event(_id)
                if curr != -1:
                    self.current_event[_id] = curr
        else:
            self.df = pd.DataFrame(
                index=[
                    "team",
                    "captain",
                    "event_order",
                    *[f"event_{i}" for i in range(event_number)],
                    "total"
                ]
            )

    def _calc_current_event(self, _id):
        curr = -1
        for i in range(self.event_number):
            if self.df[_id][f'event_{i}']['ans'] is None and self.df[_id][f'event_{i}']['time'] is not None:
                curr = i
                break
        return curr



    def _correct_order(self, order):
        matches = 0
        for team in self.df:
            matches += self.df[team]["event_order"].index(self.spec_event_num) == \
                       order.index(self.spec_event_num)
        return matches <= 3

    def add_new_team(self):
        token = str(uuid4())[:8]
        event_order = list(range(self.event_number))
        random.shuffle(event_order)
        while not self._correct_order(event_order):
            random.shuffle(event_order)
        # noinspection PyTypeChecker
        self.df.insert(
            0,
            token,
            [
                None,
                None,
                event_order,
                *[{"ans": None, "time": None} for i in range(self.event_number)],
                None
            ]
        )
        return token

    def get_tokens(self):
        tokens = []
        for team in self.df:
            if self.df[team]["team"] is None:
                tokens.append(team)
        return tokens

    def get_teams(self):
        teams = {}
        for team in self.df:
            if self.df[team]["team"] is not None:
                teams[self.df[team]["team"]] = self.df[team]["captain"]
        return teams

    def has_token(self, token):
        return token in self.df.columns

    def backup(self, count_total=False):
        if count_total:
            for _id in self.df:
                total = sum(self.df[_id][f'event_{i}']['time'] for i in range(self.event_number))
                self.df[_id]['total'] = total
        self.df.to_excel("results.xlsx", sheet_name="Результаты")

    def first_question(self, _id):
        return self.df[_id]["event_0"]['time'] is None

    def get_curr_question(self, _id):
        return f'question{self.current_event[_id]}'

    def finish(self, _id):
        return self.df[_id][f'event_{self.event_number-1}']['ans'] is not None

    def get_next_question(self, _id, ans):
        if _id in self.current_event:
            ev = self.df[_id]['event_order'][self.current_event[_id]]
            self.df[_id][f"event_{ev}"]['time'] = (datetime.datetime.now() -
                                                   self.df[_id][f"event_{ev}"]['time']).seconds
            self.df[_id][f"event_{ev}"]['ans'] = ans
        else:
            self.current_event[_id] = -1
        self.current_event[_id] += 1
        if self.current_event[_id] == self.event_number:
            return
        ev = self.df[_id]['event_order'][self.current_event[_id]]
        self.df[_id][f"event_{ev}"]['time'] = datetime.datetime.now()
        return f'question{self.current_event[_id]}'

