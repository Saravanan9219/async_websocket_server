#! /bin/python3


class LoopingList(object):

    def __init__(self):
        self.__list = []
        self.__index = 0

    def next(self):
        try:
            item = self.__list[self.__index]
        except IndexError:
            raise Exception("Empty")
        self.__index = (self.__index + 1) % len(self.__list)
        return item

    def __len__(self):
        return len(self.__list)

    def add(self, item):
        self.__list.append(item)

    def remove(self, item):
        try:
            self.__list.remove(item)
            self.__index += - 1
        except ValueError:
            raise Exception("Not Found")

