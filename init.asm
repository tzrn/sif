format ELF64 executable 3
entry start

;rbx is the stack pointers
;r12 is the current arena alloc stack's pointer
STACK_SIZE = 1024
ARENA_SIZE = 64

segment readable writeable
dstack          rq      STACK_SIZE				;reserve 1024 qwords
arena           rq      ARENA_SIZE				;stack of pointers to heap allocations
numstr          rb      16						;for converting numbers to strings
numstrlen       equ     16
argc            dq      ?
argv            dq      ?
envp            dq      ?

segment readable executable
;; FLOW CONTROL
if_:
	add     rbx, 8
; cond [v1] v2
	cmp     qword [rbx+8], 0
	jnz     .true

;false
	mov     rax, [rbx-8]
	jmp     .endif

.true:
	mov     rax, [rbx]

.endif:
	add     rbx, 8
	mov     [rbx], rax
	ret

false:
	sub     rbx, 8
	mov     qword [rbx], 0
	ret

true:
	sub     rbx, 8
	mov     qword [rbx], 1
	ret

go:
	mov     rax, [rbx]
	add     rbx, 8
	call    rax
	ret

jump:
	mov     rax, [rbx]
	add     rbx, 8
	jmp     rax
	ret

;; ARITHMETIC
sum:
	mov     rax, [rbx]
	add     rbx, 8
	add     rax, [rbx]
	mov     [rbx], rax
	ret

subtract:
	add     rbx, 8
	mov     rax, [rbx]
	sub     rax, [rbx-8]
	mov     [rbx], rax
	ret

;; IO
strlen:
	mov     rdx, [rbx]							;start
	mov     rax, rdx							;ptr
	add     rbx, 8
.start:
	cmp     byte [rax], 0
	jz      .endl
	inc     rax
	jmp     .start
.endl:
	sub     rax, rdx
	inc     rax
	ret

print:
	mov     rdi, 0
	call    copy
	call    strlen
	mov     rdx, rax							;string len
	mov     rax, 1								;sys_write
	mov     rdi, 1								;stdout
	mov     rsi, [rbx]							;string
	add     rbx, 8								;pop
	syscall
	ret

print_int:
	mov     rdi, numstr
	add     rdi, numstrlen
	mov     byte [rdi], 0

	mov     rax, [rbx]							;number
	add     rbx, 8								;pop
	mov     rcx, 10

	xor     r8, r8
	cmp     rax, 0								;is negative
	jge     .positive
	mov     r8, 1
	neg     rax

.positive:
.loop:
	xor     rdx, rdx
    ; RDX:RAX / RCX ; rax quotient, rdx remainder
	div     rcx
	dec     rdi
	add     rdx, '0'
	mov     byte [rdi], dl
	test    rax, rax
	jnz     .loop

	test    r8, r8								;is negative
	jz      .end
	dec     rdi
	mov     byte [rdi], '-'

.end:
	sub     rbx, 8
	mov     qword [rbx], rdi
	call    print

	ret


;; STACK
drop:
	add     rbx, 8
	ret

swap:
	add     rdi, rbx

	mov     rdx, [rdi]
	mov     r8, [rbx]

	mov     [rbx], rdx
	mov     [rdi], r8
	ret

copy:
	add     rdi, rbx
	mov     rax, [rdi]
	sub     rbx, 8
	mov     [rbx], rax
	ret

;; MEMORY
alloc:
	mov     rsi, [rbx]							;size (in pages)
	imul    rsi, 4096
	mov     [r12], rsi
	sub     r12, 8

	mov     rax, 9								;mmap
	xor     rdi, rdi							;addr 0 = any is fine
	mov     rdx, 3								;PROT_READ|PROT_WRITE
	mov     r10, 0x22							;MAP_PRIVATE|MAP_ANONYMOUS
	mov     r8, -1
	xor     r9, r9
	syscall

	test    rax, rax
	js      exit								;jump if sign (<0)

	mov     [r12], rax
	mov     [rbx], rax
	sub     r12, 8
	ret

free:
	cmp     r12, arena+ARENA_SIZE
	jz      .end

	mov     rax, 11								;munmap
	mov     rsi, [r12+16]						;length
	mov     rdi, [r12+8]						;addr
	syscall

	add     r12, 16
	jmp     free

.end:
	ret

set:
	mov     r8, [rbx+16]						;list
	mov     r9, [rbx+8]							;index
	imul    r9, 8
	mov     r10, [rbx]							;value
	add     rbx, 16

	add     r8, r9
	mov     [r8], r10
	ret

get:
	mov     r8, [rbx+8]							;list
	mov     r9, [rbx]							;index
	imul    r9, 8

	add     r8, r9
	mov     rax, [r8]
	mov     [rbx], rax
	ret

exit:
	mov     rax, 60								;exit
	xor     rdi, rdi							;exit code
	syscall

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
