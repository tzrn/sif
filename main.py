with open("source.ft", "r") as f:
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
    raise Exception(f"{line}:{char} {text}")


def get_until(endings):
    global c, line
    startline, startchar = line, char
    s = ""
    while True:
        if i >= l or source[i] == "#":
            err(
                f"token that starts on line {startline}:{startchar} expects any of [{endings}] to follow it"
            )
        c = source[i]
        if c in endings:
            return s
        if c == "\n":
            line += 1
        s += c
        nextc()


cmds = {
    "pr": ("print", ([str], [])),
    ".": ("endmarker", ([], [])),
    "if": ("if_", ([int, 1, 1], [1])),
    "nop": ("np", ([], [])),
    "sub": ("subtract", ([int, int], [int])),
    "add": ("sum", ([int, int], [int])),
    "ipr": ("print_int", ([int], [])),
    "dup": ("dupl", ([1], [1, 1])),
    # * "go": ("go",),
    # ! "jmp": ("jump", ([any], [])),
}

nfunc = 0
data = []
funcstack = []
typestack = []
funcdefs = ""
code = [""]
sep = ["\n", " ", "\t"]


def cmd(t):
    if t in cmds:
        return cmds[t]
    return t


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


types = {
    "int": int,
    "str": str,
}


def get_type(t):
    if t in types:
        return types[t]
    raise err(f"invalid type {t}")


def read_type():
    def read_func():
        t = []
        while source[i] != "]":
            nextc()
            t.append(read_type())
        nextc()
        return t

    if source[i] == "[":
        param = read_func()
        ret = []
        if source[i] == "[":
            ret = read_func()
        return (param, ret)
    else:
        t = get_until([",", "]"])
        try:
            return int(t)
        except ValueError:
            return get_type(t)


while i < l:
    c = source[i]
    match c:
        case '"':
            nextc()
            s = get_until(['"'])
            nextc()
            n = len(data)
            push(f"d{n}", str)
            data.append(s)
        case " " | "\t":
            nextc()
        case "\n":
            nextl()
        case "#":
            nextc()
            get_until("\n")
            nextl()
        case "&":  # command adress
            nextc()
            push(*cmd(get_until(sep)))
        case "@":
            code.append("")

            nextc()
            f = get_until(["["])
            typ = read_type()
            if f in cmds:
                err(f"attempt to shadow {t}")
            funcstack.append((f, typ[1], len(typestack)))
            typestack += typ[1]

            fname = f"f{nfunc}"
            if f and f[-1] == "&":
                f = f[:-1]
                curr = funcstack.pop()
                push(fname, typ)
                funcstack.append(curr)

            emit(f"{fname}:\n")
            if f != "":  # otherwise lambda
                cmds[f] = (fname, typ)
            nfunc += 1
        case ";":  # TODO: check that the ret from funcstack.pop matches the stack
            nextc()
            emit("ret\n\n")
            funcdefs += code.pop()
            f, ret, frame_start = funcstack.pop()
            retlen = len(ret)

            n = len(typestack)
            for val in ret:
                n -= 1
                if not typestack or val != typestack[n]:
                    err(
                        f"function {f} must return {ret} but top of your stack is {typestack[-len(ret):]}"
                    )

            typestack = typestack[:-retlen]
            lendiff = len(typestack) - frame_start
            if lendiff < 0:
                err(
                    f"function {f} must return {ret} but you are {-lendiff} values short"
                )
            if lendiff > 0:
                err(
                    f"function {f} must return {ret} but you pushed {lendiff} values too many"
                )
        case ".":
            nextc()
            t = get_until(sep)
            if not t in cmds:
                err(f"undefined function {t}")
            f, typ = cmd(t)

            n = len(typestack)
            params = typ[0]
            if n < len(params):
                err(f"function {t} requires {typ} but stack is too small: {typestack}")

            generics = {}
            n -= len(params)
            ret = []
            for param in params:
                if isinstance(param, int):
                    if param in generics and generics[param] != typestack[n]:
                        err(f"generic type '{param}' was given different types")
                    else:
                        generics[param] = typestack[n]
                elif param != typestack[n]:
                    err(
                        f"function {t} requires {params} but the top of your stack is: {typestack[-len(params):]}"
                    )
                n += 1
            typestack = typestack[: -len(params)]

            for ret in typ[1]:
                if isinstance(ret, int):
                    if not ret in generics:
                        err(
                            f"you cannot use generic '{ret}' because it wasn't in {t}'s inputs"
                        )
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
lea rbx, [dstack+1000*8] ;load effective address, top of the data stack"""

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
