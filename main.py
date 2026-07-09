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
    # "mem": ("mem", ([int], [mem])),
    # special logic in case "."
    "jmp": ("jump", ([1], [])),
    "go": ("go", ([1], [])),
}

nfunc = 0
data = []
funcstack = []
typestack = []
arenastack = []
funcdefs = ""
code = [""]
sep = ["\n", " ", "\t", "(", ";"]


def cmd(t):
    if t in cmds:
        return cmds[t]
    err(f"undefined function {t}")


def emit(s):
    code[len(funcstack)] += s


def push(val, typ):
    emit(
        f"""
sub rbx, 8 ; push {typ} onto stack
mov qword [rbx], {val}
"""
    )
    typestack.append(typ)


class Arena:
    def __init__(self):
        self.childrefs = 0


class Mem:
    def __init__(self, typ):
        self.typ = typ
        self.refs = 0


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


def same_type_lists(a, b):
    if len(a) != len(b):
        return False
    for i in range(len(a)):
        if not same_types(a[i], b[i]):
            return False
    return True


def same_types(a, b):
    if isinstance(a, Mem):
        while isinstance(a, Mem):
            if not isinstance(b, Mem):
                return False
            a = a.type
            b = b.type
        return same_types(a, b)

    if isinstance(a, tuple):
        if not isinstance(b, tuple):
            return False
        return same_type_lists(a[0], b[0]) and same_type_lists(a[1], b[1])

    return a == b


while i < l:
    c = source[i]
    match c:
        case '"':
            nextc()
            s = get_until(['"'], escape=True)
            nextc()
            n = len(data)
            push(f"d{n}", str)
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
            push(*cmd(get_until(sep)))
        case "*":
            size = typestack.pop()
            if not size == int:
                err(f"invalid mem size {size}")
            if len(arenastack) == 0:
                err(f"memory allocation outside of an arena")

            nextc()
            typ = read_type()
            mem = Mem(typ)
            mem.refs = 1
            arena = arenastack[len(arenastack) - 1]
            arena.childrefs += 1

            push(mem, Mem)
        case "{":
            nextc()
            arenastack.append(Arena())
        case "}":
            nextc()
            arenastack.pop()
        case "@":
            nextc()

            f = get_until(["["])
            typ = read_type()
            if f in cmds:
                err(f"attempt to shadow @{f}")

            fname = f"f{nfunc}"
            if f == "":
                push(fname, typ)

            code.append("")
            funcstack.append((f, typ[1], len(typestack)))
            typestack += typ[0]

            emit(f"{fname}:\n")
            if f != "":  # otherwise lambda
                cmds[f] = (fname, typ)
            nfunc += 1
        case ";":
            nextc()
            emit("ret\n\n")
            funcdefs += code.pop()
            f, ret, frame_start = funcstack.pop()

            top = typestack[frame_start:]
            if not same_type_lists(ret, top):
                err(f"function @{f} must return {ret} but you're returning {top}")
            typestack = typestack[:frame_start]
        case ".":
            nextc()
            t = get_until(sep)
            if not t in cmds:
                err(f"undefined function .{t}")
            f, (params, rets) = cmd(t)

            n = len(typestack)
            print(f"calling {t}, {typestack}, {n}>{len(params)}")
            if t == "jmp" or t == "go":
                callee = typestack.pop()
                n -= 1
                if not isinstance(callee, tuple):
                    err(f"{t} takes a function, but got {callee}")
                params, rets = callee

            if n < len(params):
                err(f".{t} requires {params} but the stack is too short: {typestack}")

            generics = {}
            n -= len(params)
            for param in params:
                if isinstance(param, int):
                    if param in generics and generics[param] != typestack[n]:
                        err(
                            f"generic type '{param}' was given different types - {typestack[n]} and {generics[param]} when calling .{t}"
                        )
                    else:
                        generics[param] = typestack[n]
                elif not same_types(param, typestack[n]):
                    err(
                        f".{t} requires {params} but the top of your stack is: {typestack[-len(params):]}"
                    )
                n += 1

            typestack = typestack[: len(typestack) - len(params)]
            for ret in rets:
                if isinstance(ret, int):
                    typestack.append(generics[ret])
                else:
                    typestack.append(ret)
            emit(f"call {f}\n")
        case _:
            t = get_until(sep)
            try:
                t = int(t)
                emit(f"mov rax, [d{len(data)}]")
                push("rax", int)
                data.append(t)
            except ValueError:
                err(f"unexpected token '{t}'")

start = """start:
lea rbx, [dstack+1000*8] ;load effective address, top of the data stack

mov rax, [rsp]
mov [argc], rax

add rax, 2 ; argc, NULL
shl rax, 3
add rax, rsp
mov [envp], rax

lea rax, [rsp+8]
mov [argv], rax
"""

end = """;exit
mov rax, 60 ;exit
xor rdi, rdi ;exit code
syscall
"""

dat = "segment readable\n"
for i in range(len(data)):
    t = data[i]
    if isinstance(data[i], str):
        dat += f'd{i} db "{t}", 10, 0\n'
    elif isinstance(data[i], int):
        dat += f"d{i} dq {t}\n"

with open("init.asm", "r") as init:
    print(init.read(), funcdefs, start, code[0], end, dat, sep="\n", end="")
