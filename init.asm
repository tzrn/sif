format ELF64 executable 3
entry start

segment readable writeable
dstack          rq      1024					;reserve 1024 qwords
numstr          rb      16						;for converting numbers to strings
numstrlen       equ     16

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

np:
	ret

endmarker:
	sub     rbx, 8
	mov     qword [rbx], 0
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
	call    dupl
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


;; stack
dupl:
	mov     qword rax, [rbx]
	sub     rbx, 8
	mov     qword [rbx], rax
	ret

swap:
	mov     rax, [rbx]
	mov     rcx, [rbx+8]
	mov     [rbx], rcx
	mov     [rbx+8], rax
	ret

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
