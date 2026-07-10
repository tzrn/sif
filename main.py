import sys

with open(sys.argv[1], "r") as f:
    source = f.read() + " "

i = 0
l = len(source)
line = 1
char = 1


def nextc():
    global i, char
    i += 1
    char += 1


def nextl():
    global line, char, i
    i += 1
    line += 1
    char = 1


def err(text):
    raise Exception(f"\033[41m{line}:{char} {text}\033[0m")


def get_until(endings, escape=False):
    global c, line
    startline, startchar = line, char
    s = ""
    while True:
        if i >= l:
            err(
                f"token that starts on line {startline}:{startchar} expects any of {endings} to follow it"
            )
        c = source[i]
        if c in endings:
            return s

        if c == "\n":
            if escape:
                s += '",10,"'
                nextl()
                continue
            line += 1
        elif escape and c == "\\" and i < l:
            nextc()
            c = source[i]
            if c == "n":
                c = '",10,"'
            elif c == '"':
                c = '",34,"'

        s += c
        nextc()


class Arena:
    pass


class Mem:
    def __init__(self, typ):
        self.typ = typ


class Frame:
    def __init__(self, name, param, ret):
        self.param = param
        self.ret = ret
        self.name = name

        self.code = f""
        self.typestack = []

    def emit(self, s):
        self.code += s

    def push(self, val, typ):
        self.emit(
            f"""sub rbx, 8 ; push {typ} onto stack
mov qword [rbx], {val}\n"""
        )
        self.typestack.append(typ)

    def pop(self):
        return self.typestack.pop()


cmds = {
    "pr": ("print", ([str], [])),
    "if": ("if_", ([int, 1, 1], [1])),
    "nop": ("np", ([], [])),
    "sub": ("subtract", ([int, int], [int])),
    "add": ("sum", ([int, int], [int])),
    "ipr": ("print_int", ([int], [])),
    "dup": ("dupl", ([1], [1, 1])),
    "swap": ("swap", ([1, 2], [2, 1])),
    "drop": ("drop", ([1], [])),
    "set": ("set", ([Mem(1), int, 1], [])),
    "get": ("get", ([Mem(1), int], [1])),
    # special logic in case "."
    "jmp": ("jump", ([1], [])),
    "go": ("go", ([1], [])),
}

nfunc = 0
data = []
arena = None
sep = ["\n", " ", "\t", "(", ";", "."]
code = []
currframe = Frame("main", [], [])
frames = [currframe]


def cmd(t):
    if t in cmds:
        return cmds[t]
    err(f"undefined function {t}")


types = {"int": int, "str": str, "mem": Mem}


def get_type(t):
    if t in types:
        return types[t]
    raise err(f"invalid type {t}")


def read_type_list():
    t = []
    nextc()
    while source[i] != "]":
        t.append(read_type())
        if source[i] == ",":
            nextc()
    nextc()
    return t


def read_type():
    if source[i] == "[":
        param = read_type_list()
        ret = []
        if source[i] == "[":
            ret = read_type_list()
            for r in ret:
                if isinstance(r, int) and not r in param:
                    err(f"you cannot use generic '{ret}' because it wasn't in inputs")
        return (param, ret)
    elif source[i] == "*":
        nextc()
        return Mem(read_type())
    else:
        t = get_until(sep + [",", "]"])
        try:
            return int(t)
        except ValueError:
            return get_type(t)


def same_type_lists(a, b, generics={}):
    if len(a) != len(b):
        return False
    for i in range(len(a)):
        if not same_types(a[i], b[i], generics):
            return False
    return True


def same_types(a, b, generics={}):
    if isinstance(a, Mem):
        while isinstance(a, Mem):
            if not isinstance(b, Mem):
                return False
            a = a.typ
            b = b.typ
        return same_types(a, b, generics)

    if isinstance(a, tuple):
        if not isinstance(b, tuple):
            return False
        return same_type_lists(a[0], b[0]) and same_type_lists(a[1], b[1])

    if isinstance(a, int):  # b is from stack thus never generic
        if a in generics:
            a = generics[a]
        else:
            generics[a] = b
            return True

    return a == b


while i < l:
    c = source[i]
    match c:
        case '"':
            nextc()
            s = get_until(['"'], escape=True)
            nextc()
            n = len(data)
            currframe.push(f"d{n}", str)
            data.append(s)
        case " " | "\t":
            nextc()
        case "\n":
            nextl()
        case "(":
            nextc()
            get_until(")")
            nextc()
        case "&":  # command adress
            nextc()
            currframe.push(*cmd(get_until(sep)))
        case "*":
            nextc()
            size = currframe.pop()
            if not size == int:
                err(f"invalid mem size {size}")
            if arena == None:
                err(f"memory allocation outside of an arena")

            typ = read_type()
            mem = Mem(typ)

            currframe.typestack.append(mem)
            currframe.emit("call alloc\n")
        case "{":
            nextc()
            if arena is not None:
                err("nested arenas aren't allowed")
            arena = Arena()
        case "}":
            nextc()
            arena = None
            currframe.emit("call free\n")
        case "@":
            nextc()

            f = get_until(["["])
            param, ret = read_type()
            if f in cmds:
                err(f"attempt to shadow @{f}")

            fname = f"f{nfunc}"
            nfunc += 1
            if f == "":  # lambda
                currframe.push(fname, (param, ret))
            else:
                cmds[f] = (fname, (param, ret))

            currframe = Frame(f, param, ret)
            frames.append(currframe)
            currframe.typestack += param

            currframe.emit(f"{fname}:\n")
        case ";":
            nextc()
            currframe.emit("ret\n\n")

            byeframe = frames.pop()
            code.append(byeframe.code)
            currframe = frames[len(frames) - 1]

            if not same_type_lists(byeframe.typestack, byeframe.ret):
                err(
                    f"function @{byeframe.name} must return {byeframe.ret} but you're returning {byeframe.typestack}"
                )
        case ".":
            nextc()
            t = get_until(sep)
            if not t in cmds:
                err(f"undefined function .{t}")
            f, (params, rets) = cmd(t)
            # print(f"calling {t}, {currframe.typestack}")

            if t == "jmp" or t == "go":
                callee = currframe.pop()
                if not isinstance(callee, tuple):
                    err(f"{t} takes a function, but got {callee}")
                params, rets = callee

            stacklen = len(currframe.typestack)
            paramlen = len(params)
            if stacklen < paramlen:
                err(
                    f".{t} requires {params} but the stack is too short: {currframe.typestack}"
                )

            generics = {}
            if not same_type_lists(
                params, currframe.typestack[stacklen - paramlen :], generics
            ):
                err(
                    f".{t} requires {params} but the top of your stack is: {currframe.typestack[-len(params):]}"
                )

            currframe.typestack = currframe.typestack[
                : len(currframe.typestack) - len(params)
            ]
            for ret in rets:
                if isinstance(ret, int):
                    currframe.typestack.append(generics[ret])
                else:
                    currframe.typestack.append(ret)
            currframe.emit(f"call {f}\n")
        case _:
            t = get_until(sep)
            try:
                t = int(t)
                currframe.emit(f"mov rax, [d{len(data)}]\n")
                currframe.push("rax", int)
                data.append(t)
            except ValueError:
                err(f"unexpected token '{t}'")

main = frames.pop().code
funcdefs = "\n".join(code)

start = """start:
lea rbx, [dstack+STACK_SIZE] ;load effective address, top of the data stack
mov r12, arena+ARENA_SIZE ;arena stack ptr

mov rax, [rsp]
mov [argc], rax

add rax, 2 ; skip argc, NULL
shl rax, 3
add rax, rsp
mov [envp], rax

lea rax, [rsp+8]
mov [argv], rax
"""

end = """exit:
mov rax, 60 ;exit
xor rdi, rdi ;exit code
syscall
"""

dat = "segment readable\n"
for i in range(len(data)):
    t = data[i]
    if isinstance(data[i], str):
        dat += f'd{i} db "{t}", 0\n'
    elif isinstance(data[i], int):
        dat += f"d{i} dq {t}\n"

with open("init.asm", "r") as init:
    print(init.read(), funcdefs, start, main, end, dat, sep="\n", end="")
