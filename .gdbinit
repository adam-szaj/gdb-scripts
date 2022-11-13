set auto-load safe-path /
set print pretty on
set print object on
set print static-members on
set print vtbl on
set print demangle on
set demangle-style gnu-v3
set print sevenbit-strings off
set pagination off
set confirm off
set history save on
set breakpoint pending on

define tt
    thread $arg0
    bt
end

define it
    info threads
end

source ~/.gdb/find_deadlock.py
