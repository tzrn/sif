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
    raise Exception(f"\033[41m(@{currframe.name}) {line}:{char} {text}\033[0m")


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


class Condition:
    def __init__(self, num):
        self.starttypestack = []
        self.falsebranchstack = []
        self.num = num


class Frame:
    def __init__(self, name, param, ret, cmds):
        self.param = param
        self.ret = ret
        self.name = name
        self.cmds = cmds

        self.code = f""
        self.typestack = []
        self.ncond = 0
        self.condstack = []

    def emit(self, s):
        self.code += s

    def push(self, val, typ):
        self.emit(
            f"""sub r10, 8 ; push {typ} onto stack
mov qword [r10], {val}\n"""
        )
        self.typestack.append(typ)

    def pop(self):
        return self.typestack.pop()


default_cmds = {
    "pr": ("print", ([str], [])),
    "sub": ("subtract", ([int, int], [int])),
    "add": ("sum", ([int, int], [int])),
    "mul": ("multiply", ([int, int], [int])),
    "div": ("divide", ([int, int], [int, int])),
    "ipr": ("print_int", ([int], [])),
    "set": ("set", ([Mem(1), int, 1], [Mem(1)])),
    "get": ("get", ([Mem(1), int], [Mem(1), 1])),
    "not": ("not_", ([int], [int])),
    "isneg": ("isneg", ([int], [int])),
    "and": ("and_", ([int, int], [int])),
    # special logic in case "."
    "ret": ("return", ([], [])),
    "loop": ("_loop", ([], [])),
    "go": ("go", ([1], [])),
}

nfunc = 0
data = {}
arena = None
sep = ["\n", " ", "\t", "(", ";"]
argregs = ["rdi", "rsi", "rdx", "rcx", "r8", "r9"]
floatargregs = ["xmm0", "xmm1", "xmm2", "xmm3", "xmm4", "xmm5", "xmm6", "xmm7"]
extern = ""
code = []
currframe = Frame("main", [], [], default_cmds)
frames = [currframe]


def cmd_exists(t):
    for i in range(len(frames) - 1, -1, -1):
        if t in frames[i].cmds:
            return frames[i].cmds[t]
    return False


def cmd(t):
    c = cmd_exists(t)
    if not c:
        err(f"undefined function {t}")
    return c


types = {"int": int, "str": str, "float": float, "mem": Mem}


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

    if isinstance(a, int):
        if isinstance(b, int):
            return a == b
        if a in generics:
            a = generics[a]
            return same_types(a, b)
        else:
            generics[a] = b
            return True

    return a == b


def replace_generics_list(arr, generics):
    new = []
    for i in range(len(arr)):
        new.append(replace_generics(arr[i], generics))
    return new


def replace_generics(a, generics):
    if isinstance(a, int):
        if a in generics:
            return generics[a]
        return a
    if isinstance(a, Mem):
        return Mem(replace_generics(a.typ, generics))
    if isinstance(a, tuple):
        param, ret = a
        return (
            replace_generics_list(param, generics),
            replace_generics_list(ret, generics),
        )
    return a


def scan_functype():
    if source[i] == "[":
        return read_type()
    elif source[i] == ":":
        nextc()
        t = get_until(sep)
        _, (param, ret) = cmd(t)
        return (param, ret)
    else:
        return ([], [])


def data_name(value):
    if not value in data:
        n = len(data)
        data[value] = n
    else:
        n = data[value]
    return n


def stack_move(swap, fromBottom):
    index = get_until(sep)

    try:
        index = int(index)
    except ValueError:
        err(f"invalid index {index}")

    if index >= len(currframe.typestack) or index < 0:
        err(
            f"index {index} is referencing a value beyond the stack {currframe.typestack}"
        )

    n = len(currframe.typestack) - 1
    if fromBottom:
        index = n - index
    currframe.emit(f"mov rdi, {index*8}\n")
    index = n - index
    if swap:
        a = currframe.typestack[index]
        currframe.typestack[index] = currframe.typestack[n]
        currframe.typestack[n] = a
        currframe.emit("call swap\n")
    else:  # copy
        currframe.typestack.append(currframe.typestack[index])
        currframe.emit("call copy\n")


while i < l:
    c = source[i]
    match c:
        case '"':
            nextc()
            s = get_until(['"'], escape=True)
            nextc()
            currframe.push(f"d{data_name(s)}", str)
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
            if len(currframe.typestack) < 1:
                err("need a mem size but the stack is empty")
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
                # because it's hard to check if you hide
                # a memory in another arena's memory
                err("nested arenas aren't allowed")
            arena = Arena()
        case "}":
            nextc()
            for t in currframe.typestack:
                if isinstance(t, Mem):
                    err(f"memory is on the stack beyond an arena {currframe.typestack}")
            arena = None
            currframe.emit("call free\n")
        case "@":
            nextc()

            f = get_until(["[", ":"] + sep)
            param, ret = scan_functype()
            if cmd_exists(f):
                err(f"attempt to shadow @{f}")

            fname = f"f{nfunc}"
            nfunc += 1
            if f == "":  # lambda
                currframe.push(fname, (param, ret))
            else:
                currframe.cmds[f] = (fname, (param, ret))

            currframe = Frame(f, param, ret, {})
            frames.append(currframe)
            currframe.typestack += param

            currframe.emit(f"{fname}:;{f}\nmov rax, {fname}\npush rax\n")
        case "!":
            nextc()
            f = get_until(["[", ":"])
            param, ret = scan_functype()
            if cmd_exists(f):
                err(f"attempt to shadow @{f}")
            if len(ret) > 1:
                err("external function cannot return multiple values")

            fname = f"f{nfunc}"
            currframe.cmds[f] = (fname, (param, ret))
            nfunc += 1

            extern += f"extrn {f}\n{fname}:\n"
            ii = 0
            fi = 0
            extern += f"add r10,{len(param)*8}\n"
            offset = 8
            for j in range(len(param)):
                if param[j] == float:
                    extern += f"movss {floatargregs[fi]}, [r10-{offset}]\n"
                    fi += 1
                else:
                    extern += f"mov {argregs[ii]}, [r10-{offset}]\n"
                    ii += 1
                offset += 8

            extern += f"push r10\npush r11\ncall {f}\npop r11\npop r10\n"
            if len(ret) == 1:
                extern += f"sub r10,8\nmov [r10],rax\n"
            extern += "ret\n\n"
        case ";":
            nextc()
            currframe.emit("add rsp, 8\nret\n\n")

            byeframe = frames.pop()
            code.append(byeframe.code)
            currframe = frames[-1]

            if not same_type_lists(byeframe.typestack, byeframe.ret):
                err(
                    f"function @{byeframe.name} must return {byeframe.ret} but you're returning {byeframe.typestack}"
                )
        case "<":
            nextc()
            swap = source[i] == ">"
            if swap:
                nextc()
            stack_move(swap, False)
        case ">":
            nextc()
            swap = source[i] == "<"
            if swap:
                nextc()
            stack_move(swap, True)
        case ",":
            nextc()
            n = get_until(sep)
            try:
                n = int(n)
            except ValueError:
                err(f"expected a number but got  -{n}")

            stacklen = len(currframe.typestack)
            if n > stacklen:
                err(f"trying to drop {n} elements but the stack is only {stacklen}")
            currframe.typestack = currframe.typestack[: stacklen - n]
            currframe.emit(f"mov rdi, {n*8}\ncall drop\n")
        case ".":
            nextc()
            t = get_until(sep)
            # print(f"calling {t}, {currframe.typestack}")
            f, (params, rets) = cmd(t)

            if t == "ret":
                if not same_type_lists(currframe.typestack, currframe.ret):
                    err(
                        f"function @{currframe.name} must return {currframe.ret} but you're returning {currframe.typestack}"
                    )
                params = []
                rets = []
            elif t == "loop":
                rets = currframe.ret
                params = currframe.param
            elif t == "go":
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
            currframe.typestack += replace_generics_list(rets, generics)
            currframe.emit(f"call {f} ;{t}\n")
        case "?":
            nextc()
            cond = currframe.typestack.pop()
            if not cond == int:
                err("condition must be an integer")

            cond = Condition(currframe.ncond)
            cond.starttypestack = currframe.typestack.copy()
            currframe.ncond += 1
            currframe.emit(
                f"""
            add r10, 8 ;if
            mov rax, [r10-8]
            test rax,rax
            jz .false{cond.num}
            """
            )
            currframe.condstack.append(cond)
        case ":":
            nextc()
            cond = currframe.condstack[-1]
            currframe.emit(f"jmp .endif{cond.num}\n.false{cond.num}:\n")
            cond.truebranchtypes = currframe.typestack.copy()
            currframe.typestack = cond.starttypestack
        case "$":
            nextc()
            cond = currframe.condstack.pop()
            if not same_type_lists(cond.truebranchtypes, currframe.typestack):
                err(
                    "condition branches must produce the same stack but you have\n"
                    + f"true: {cond.truebranchtypes}\nfalse:{currframe.typestack}"
                )
            currframe.emit(f".endif{cond.num}:\n")
        case "#":
            nextc()
            t = get_until(sep)
            try:
                t = int(t, 16)
                currframe.emit(f"mov rax, {t} ;int\n")
                currframe.push("rax", int)
            except ValueError:
                err(f"expected a hex number but got x'{t}'")
        case "~":
            nextc()
            t = read_type()
            if len(currframe.typestack) < 1:
                err("trying to assert a type but the stack is empty")
            currframe.typestack[-1] = t
        case "f":
            nextc()
            t = get_until(sep)
            try:
                t = float(t)
                currframe.emit(
                    f"movss xmm0, [d{data_name(t)}] ;float\nsub r10, 8\nmovss [r10],xmm0\n"
                )
                currframe.typestack.append(float)
            except ValueError:
                err(f"expected a float but got f'{t}'")
        case _:
            t = get_until(sep)
            try:
                t = int(t)
                currframe.emit(f"mov rax, {t} ;int\n")
                currframe.push("rax", int)
            except ValueError:
                err(f"unexpected token '{t}'")

main = frames.pop().code
funcdefs = "\n".join(code)

start = """main:
lea r10, [dstack+STACK_SIZE] ;load effective address, top of the data stack
mov r11, arena+ARENA_SIZE ;arena stack ptr

mov rax, [rsp]
mov [argc], rax

add rax, 2 ; skip argc, NULL
shl rax, 3
add rax, rsp
mov [envp], rax

lea rax, [rsp+8]
mov [argv], rax
"""

dat = "section '.data'\n"
for d in data:
    i = data[d]
    if isinstance(d, str):
        dat += f'd{i} db "{d}", 0\n'
    elif isinstance(d, float):
        dat += f"d{i} dd {d}\n"

with open("init.asm", "r") as init:
    print(init.read(), extern, funcdefs, start, main, "jmp exit", dat, sep="\n", end="")
