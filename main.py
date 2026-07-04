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


def get_until(endings):
    startline = line
    s = ""
    while True:
        if i >= l:
            raise Exception(
                f"{line}:{char} token that starts on line {startline} is not terminated by {endings}"
            )
        c = source[i]
        if c == "\n":
            nextl()
        if c in endings:
            return s
        s += c
        nextc()


data = []
argregs = ["rdi", "rsi", "rdx", "rcx", "r8", "r9"]
sep = ["\n", " ", "\t", ";"]

cmds = {
    "pr": "print",
    ".": "endmarker",
    "if": "if_",
    "t": "true",
    "f": "false",
    "go": "go",
    "nop": "np",
    "sub": "subtract",
    "add": "sum",
    "ipr": "print_int",
    "dup": "dupl",
    "jmp": "jump",
}

code = ["", ""]  # function definitions, main code
nfunc = 0
depth = 1
cmdrefs = []


def cmd(t):
    if t in cmds:
        return cmds[t]
    cmdrefs.append((line, char, t))
    return t


def emit(s):
    code[depth] += s


def push(op):
    emit(
        f"""
sub rbx, 8
mov qword [rbx], {op}
"""
    )


while i < l:
    c = source[i]
    match c:
        case '"':
            nextc()
            s = get_until(['"'])
            nextc()
            n = len(data)
            push(f"d{n}")
            data.append(s)
        case " " | "\t":
            nextc()
        case "\n":
            nextl()
        case "#":
            while i < l and source[i] != "\n":
                nextc()
            nextl()
        case "&":  # command adress
            nextc()
            t = get_until(sep)
            push(cmd(t))
        case "@":
            code.append("")
            depth += 1

            nextc()
            t = get_until(sep)
            fname = f"f{nfunc}"
            if t and t[-1] == "&":
                t = t[:-1]
                depth -= 1
                push(fname)
                depth += 1

            if t in cmds:
                raise Exception(f"{line}:{char} attempt to shadow {t}")

            emit(f"{fname}:\n")
            if t != "":  # lambda
                cmds[t] = fname
            nfunc += 1
        case ";":
            nextc()
            emit("ret\n\n")
            code[0] += code.pop()
            depth -= 1
        case ".":
            nextc()
            t = get_until(sep)
            emit(f"call {cmd(t)}\n")
        case _:
            t = get_until(sep)
            try:
                t = int(t)
                emit(
                    f"""mov rax, [d{len(data)}]
sub rbx, 8
mov [rbx], rax
"""
                )
                data.append(t)
            except ValueError:
                raise Exception(f"{line}:{char} unexpected token '{t}'")

for l, c, t in cmdrefs:
    if not t in cmds:
        raise Exception(f"{l}:{c} reference to an undefined command {t}")

with open("init.asm", "r") as f:
    init = f.read()

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

print(init, code[0], start, code[1], end, dat, sep="\n", end="")
