# Copyright 2016 Adam Szaj <adam.szaj@gmail.com>
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

class DThread:
    def __init__(self, gdb_thread):
        self.num = gdb_thread.num
        self.name = gdb_thread.name
        self.pid = gdb_thread.ptid[0]
        self.tid = gdb_thread.ptid[1]
        self.gdb_thread = gdb_thread
        pass

    def get_tid(self):
        return self.tid

    def get_pid(self):
        return self.pid

    def get_thread(self):
        return self.gdb_thread

    def __str__(self):
        s='{} tid: {} on pid: {} [{}]'.format(self.num, self.tid, self.pid, self.name)
        return s

    def search_function(self, functions):
        frame = gdb.newest_frame()
        while frame is not None:
            name = frame.name()
            if name in functions:
                return frame
            frame = frame.older()

        return None

    def get_newest_frame(self):
        return gdb.newest_frame()
    pass

class SyscallHandler:
    def __init__(self):
        pass
    def handle(self, finder, thread, frame):
        if frame is not None:
            name = frame.name()
            print("thread: {} stopped on {}".format(str(thread), frame.name()))
        pass
    pass

class GenericMutexLockHandler:
    def __init__(self):
        pass

    def handle(self, finder, thread, frame):
        frame.select()
        owner_tid = self.get_lock_owner()
        print("thread: {} is blocked on mutex in {}".format(str(thread), frame.name()))
        owner_thread = finder.get_thread_by_tid(owner_tid)
        if owner_thread is not None:
            print("\tbut the owner of the mutex is:\n\tthread: {}\n".format(owner_thread))
        else:
            print("\tbut the owner of the mutex is: {} unknown\n".format(owner_tid))

        pass

    pass


class PthreadMutexLockHandler(GenericMutexLockHandler):
    def __init__(self):
        pass

    def get_lock_owner(self):
        return int(gdb.parse_and_eval('mutex->__data.__owner'))

    pass

class PthreadRWLockWRHandler:
    def __init__(self):
        pass

    def get_lock_owner(self):
        return int(gdb.parse_and_eval('rwlock->__data.__cur_writer'))

    def get_lock_readers(self):
        return int(gdb.parse_and_eval('rwlock->__data.__readers'))

    def handle(self, finder, thread, frame):
        frame.select()
        owner_tid = self.get_lock_owner()
        print("thread: {} (writer) is blocked on rwlock in {}".format(str(thread), frame.name()))
        owner_thread = finder.get_thread_by_tid(owner_tid)
        if owner_thread is not None:
            print("\tbut the owner of the rwlock is (writer):\n\tthread: {} \n".format(owner_thread))
        else:
            readers=self.get_lock_readers()
            if readers > 0:
                print("\tbut the rwlock is acquired by reader[s]\n")
            else:
                print("\trwlock is locked for unknown reason\n")
        pass

    pass

class PthreadRWLockRDHandler:
    def __init__(self):
        pass

    def get_lock_owner(self):
        return int(gdb.parse_and_eval('rwlock->__data.__cur_writer'))

    def handle(self, finder, thread, frame):
        frame.select()
        owner_tid = self.get_lock_owner()
        print("thread: {} (reader) is blocked on rwlock in {}".format(str(thread), frame.name()))
        owner_thread = finder.get_thread_by_tid(owner_tid)
        if owner_thread is not None:
            print("\tbut the owner of the rwlock is (writer):\n\tthread: {} \n".format(owner_thread))
        else:
            print("\trwlock is locked for unknown reason\n")
        pass
    pass

class DeadLockFinder:
    function_handlers={
            '__GI___pthread_mutex_lock': PthreadMutexLockHandler(), 
            '___pthread_mutex_lock': PthreadMutexLockHandler(), 

            '___pthread_rwlock_wrlock': PthreadRWLockWRHandler(),
            '___pthread_rwlock_rdlock': PthreadRWLockRDHandler(),

            '__libc_do_syscall': SyscallHandler(),
            'syscall': SyscallHandler()
    }
    blocking_functions = function_handlers.keys()
    
    def __init__(self):
        inf=gdb.selected_inferior()
        if inf is not None:
            if inf.is_valid():
                self.threads=[]
                selected_thread = gdb.selected_thread()
                for th in inf.threads():
                    self.threads.append(DThread(th))
                if selected_thread is not None:
                    selected_thread.switch()
        pass

    def get_thread_by_tid(self, tid):
        for thread in self.threads:
            if thread.get_tid() == tid:
                return thread
        return None

    def find_for_thread(self, thread):
        handlers = DeadLockFinder.function_handlers
        thread.get_thread().switch()
        frame = thread.search_function(functions=DeadLockFinder.blocking_functions)
        # print("thread: {}".format(str(thread)))
        if frame is not None:
            oldest_frame = frame
            older_frame = frame.older()

            while older_frame is not None:
                function_name = older_frame.name()
                if function_name in handlers.keys():
                    oldest_frame = older_frame
                older_frame = older_frame.older()

            handlers[oldest_frame.name()].handle(self, thread, oldest_frame)
        else:
            print("thread: {} is in {}".format(str(thread), thread.get_newest_frame().name()))

    def find(self):
        for thread in self.threads:
            self.find_for_thread(thread)
        pass

    pass

class FindDeadlock(gdb.Command):
    def __init__(self):
        super(FindDeadlock, self).__init__(
            "find_deadlock", gdb.COMMAND_USER
        )

    def invoke(self, args, from_tty):
        dlf = DeadLockFinder()
        dlf.find()
        pass

    pass

# register new command
FindDeadlock()

