with open("source.ft","r") as f:
    source = f.read()+" "

i=0
l=len(source)
line=1
char=1

def nextc():
    global i, char
    i+=1
    char+=1

def nextl():
    global line, char, i
    i+=1
    line+=1
    char=1

def get_until(endings):
    startline=line
    s=""
    while True:
        if i>=l:
            raise Exception(f"{line}:{char} token that starts on line {startline} is not terminated by {endings}")
        c=source[i]
        if c=='\n':
            nextl()
        if c in endings:
            return s
        s+=c
        nextc()

data=[]
argregs=["rdi","rsi","rdx","rcx","r8","r9"]
sep=["\n"," ","\t"]

cmds={
    "pr": "print",
    ".": "endmarker",
    "if": "if_",
    "t": "true",
    "f": "false",
    "go": "go",
    "np": "np",
}

code=""
funcdefs=""
snippet=""
nfunc=0
funcdepth=0

cmdrefs=[]
def cmd(t):
    if t in cmds:
        return cmds[t]
    cmdrefs.append((line,char,t))
    return t

while i<l:
    c=source[i]
    match c:
        case '"':
            nextc()
            s=get_until(['"'])
            nextc()
            n=len(data)
            snippet += f""";load str
sub rbx, 8
mov qword [rbx], d{n}
"""
            data.append(s)
        case ' ' | "\t":
            nextc()
        case '\n':
            nextl()
        case '#':
            while i<l and source[i]!='\n':
                nextc()
            nextl()
        case '&': # command adress
            nextc()
            t=get_until(sep)
            snippet+=f""";load function pointer
sub rbx, 8
mov qword [rbx], {cmd(t)}
"""
        case '@':
            nextc()
            t=get_until(sep)
            fname=f"f{nfunc}"
            if t and t[-1]=='&':
                t=t[:-1]
                snippet+=f""";push func onto stack
sub rbx, 8
mov qword [rbx], {fname}
"""

            if funcdepth==0:
                code+=snippet
            else:
                funcdefs+=snippet
            snippet=""

            if t in cmds:
                raise Exception(f"{line}:{char} attempt to shadow {t}")

            snippet+=f"{fname}:\n"
            cmds[t]=fname
            nfunc+=1
            funcdepth+=1
        case ';':
            nextc()
            if funcdepth%2==1:
                funcdefs+=snippet+"ret\n\n"
            else:
                funcdefs=snippet+"ret\n\n"+funcdefs
            snippet=""
            funcdepth-=1
        case '.':
            nextc()
            t=get_until(sep)
            snippet+=f"call {cmd(t)}\n"
        case _:
            t=get_until(sep)
            try:
                t=float(t)
                snippet+=f""";load num
sub rbx, 8
mov qword [rbx], d{len(data)}\n"""
                data.append(t)
            except ValueError:
                raise Exception(f"{line}:{char} unexpected token '{t}'")

for l, c, t in cmdrefs:
    if not t in cmds:
        raise Exception(f"{l}:{c} reference to an undefined command {t}")

init="""format ELF64 executable 3
entry start

segment readable writeable
dstack rq 1024 ;reserve 1024 qwords

segment readable executable
"""

funcdefs+="""false:
sub rbx, 8
mov qword [rbx],0
ret

true:
sub rbx, 8
mov qword [rbx],1
ret

go:
mov rax, [rbx]
add rbx, 8
call rax
ret

np:
ret

strlen:
mov rax, rdi
.start:
    cmp byte [rdi], 0
    jz .endl
    inc rdi
    jmp .start
.endl:
    sub rdi, rax
    mov rax, rdi
    inc rax
ret

print:
mov rdi, [rbx]
call strlen
mov rdx, rax ;string len

mov rax, 1 ;sys_write
mov rdi, 1 ;stdout
mov rsi, [rbx] ;string
add rbx, 8
syscall
ret

endmarker:
sub rbx, 8
mov qword [rbx], 0
ret

if_:
add rbx, 8
; cond [v1] v2
cmp qword [rbx+8], 0
jnz .true

;false
mov rax, [rbx-8]
jmp .endif
.true:
mov rax, [rbx]

.endif:
add rbx, 8
mov [rbx], rax
ret
"""

code="""start:
lea rbx, [dstack+1000*8] ;load effective addres, top of the data stack
"""+code+snippet+""";exit
mov rax, 60 ;exit
xor rdi, rdi ;exit code
syscall
"""

dat="segment readable\n"
for i in range(len(data)):
    t=data[i]
    if isinstance(data[i],str):
        dat+=f'd{i} db "{t}", 10, 0\n'
    elif isinstance(data[i],float):
        dat+=f'd{i} dq {t}\n'

print(init, funcdefs, code, dat, sep="\n", end="")

# TODO: math, stack ops, forign functions