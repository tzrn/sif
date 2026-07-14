format ELF64
public main

;r10 is the stack pointer
;r11 is the current arena alloc stack's pointer
STACK_SIZE = 1024
ARENA_SIZE = 64

section '.note.GNU-stack'
section '.bss'
dstack          rq      STACK_SIZE				;reserve 1024 qwords
arena           rq      ARENA_SIZE				;stack of pointers to heap allocations
numstr          rb      16						;for converting numbers to strings
numstrlen       equ     16
argc            dq      ?
argv            dq      ?
envp            dq      ?

section '.text'
;; FLOW CONTROL
go:
	mov     rax, [r10]
	add     r10, 8
	call    rax
	ret

return:
	add     rsp, 16								;discard return addr
	pop     rax									;caller's return addr
	jmp     rax

_loop:
	add     rsp, 8
	pop     rax
	jmp     rax

;; ARITHMETIC
sum:
	mov     rax, [r10]
	add     r10, 8
	add     rax, [r10]
	mov     [r10], rax
	ret

subtract:
	add     r10, 8
	mov     rax, [r10]
	sub     rax, [r10-8]
	mov     [r10], rax
	ret

multiply:
	mov     rax, [r10]
	mov     rdx, [r10+8]
	add     r10, 8
	imul    rax, rdx
	mov     [r10], rax
	ret

;;LOGIC
isneg:
	mov     rax, [r10]
	sar     rax, 63
	mov     [r10], rax
	ret

not_:
	mov     rax, [r10]
	not     rax
	mov     [r10], rax
	ret

;; IO
strlen:
	mov     rdx, [r10]							;start
	mov     rax, rdx							;ptr
	add     r10, 8
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
	mov     rsi, [r10]							;string
	add     r10, 8								;pop
	push    r11
	push    r10
	syscall
	pop     r10
	pop     r11
	ret

print_int:
	mov     rdi, numstr
	add     rdi, numstrlen
	mov     byte [rdi], 0

	mov     rax, [r10]							;number
	add     r10, 8								;pop
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
	sub     r10, 8
	mov     qword [r10], rdi
	call    print

	ret


;; STACK
drop:
	add     r10, rdi
	ret

swap:
	add     rdi, r10

	mov     rdx, [rdi]
	mov     r8, [r10]

	mov     [r10], rdx
	mov     [rdi], r8
	ret

copy:
	add     rdi, r10
	mov     rax, [rdi]
	sub     r10, 8
	mov     [r10], rax
	ret

;; MEMORY
alloc:
	mov     rsi, [r10]							;size (in pages)
	imul    rsi, 4096
	mov     [r11], rsi
	sub     r11, 8

	push    r10
	mov     rax, 9								;mmap
	xor     rdi, rdi							;addr 0 = any is fine
	mov     rdx, 3								;PROT_READ|PROT_WRITE
	mov     r10, 0x22							;MAP_PRIVATE|MAP_ANONYMOUS
	mov     r8, -1
	xor     r9, r9
	push    r11
	syscall
	pop     r11
	pop     r10

	test    rax, rax
	js      exit								;jump if sign (<0)

	mov     [r11], rax
	mov     [r10], rax
	sub     r11, 8
	ret

free:
	cmp     r11, arena+ARENA_SIZE
	jz      .end

	mov     rax, 11								;munmap
	mov     rsi, [r11+16]						;length
	mov     rdi, [r11+8]						;addr
	push    r11
	push    r10
	syscall
	pop     r10
	pop     r11

	add     r11, 16
	jmp     free

.end:
	ret

set:
	mov     r8, [r10+16]						;list
	mov     r9, [r10+8]							;index
	imul    r9, 8
	mov     rcx, [r10]							;value
	add     r10, 16

	add     r8, r9
	mov     [r8], rcx
	ret

get:
	mov     r8, [r10+8]							;list
	mov     r9, [r10]							;index
	imul    r9, 8

	add     r8, r9
	mov     rax, [r8]
	mov     [r10], rax
	ret

exit:
	mov     rax, 60								;exit
	xor     rdi, rdi							;exit code
	syscall

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
