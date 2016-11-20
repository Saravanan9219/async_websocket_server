#! /bin/python3

from helpers import coroutine
from looping_list import LoopingList


class PipeLine(object):
    pipe = LoopingList()

    @classmethod
    def add_job(cls, job):
        cls.pipe.add(job)
    
    @classmethod
    @coroutine
    def execute(cls):
        while True:
            pipeline_length = len(cls.pipe)
            try:
                for i in range(0, pipeline_length):
                    job = cls.pipe.next()
                    try:
                        next(job)
                    except StopIteration as e:
                        cls.pipe.remove(job)
            except Exception as e:
                yield
            yield

