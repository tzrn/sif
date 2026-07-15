# Sif

A stack based, functional language and a compiler (to Linux x86_64 fasm) for it.

## Usage

```./run [includes...] source.sif```

## Syntax

### Stack

- `1 2 3` - this puts 1, 2 and 3 onto the stack. When calling functions, they might consume stack and/or put new values on it. For example `1 2 3 .add .ipr .ipr` 1, 2 and 3 are put onto the stack, then 2 and 3 are added and printed then 1 is printed so the output is *51*.
- `<n` copies values removed by n from the top of the stack `1 2 3 <1` will copy 2 to the stack. `<0` copies the top of the stack. `<>n` will replace current element with the nth one. `>n` and `><n` work the same way but count from the bottom of the stack. For example `1 2 3 >0` will copy 1 to the top.
- `,n` drops n values. For example `1 2 3 ,2` will drop 3 and 2.
- the 3 basic type that you have are strings - `"This is a string"` (escape sequences - `"\n \" \\"`), integers - `123` (or `#FFFF00` for hex) and floats - `f1`, `f2.48`. 
- you can assert a type with `~type` for example `~float` will assert that the value on the top of the stack is float.
- anything enclosed in parentheses is ignored `(ignored)`

### Arrays

- To define array use `size *type` for example `2 *int`. Size is in pages (4096 bytes. Since each element is 8 bytes that's 512 elements).
- Arrays can be nested `1 **int 0 1 *int .set`.
- Arrays can be only defined and used in an arena:
```
{
    1 *int
    0 1 .set
    0 .get .ipr
    ,1
}
```

### Builtin functions

- @pr:  [str][] - print a string
- @sub: [int, int][int] - subtract integers
- @add: [int, int][int] - add integers
- @mul: [int, int][int] - multiply integers
- @div: [int, int][int, int] - divide two numbers, return remainder and result
- @ipr: [int][] - print an integer
- @set: [*1, int, 1][*1] - set value in an array
- @get: [*1, int][*1, 1] - get value from an array
- @not: [int][int] - logical not
- @isneg: [int][int] - returns -1 if value is negative otherwise 0
- @ret: [][] - return from function early
- @loop: [][] - jump back to the beginning of a function (tail call)
- @go: [1][] - execute a function that is on the stack

### Functions

- To define function use `@fname[params][return_values]` then put the function body and `;` at the end. For example:
```
@add3[int,int,int][int]
    .add .add
;
```
- If a function doesn't have return values [] can be omitted. If it has neither parameters nor return values then the whole signature can be omitted:
```
@greet[str]
    "Hello, " .pr .pr "\n" .pr
;
@hw
    "Hello world\n" .pr
;
```
- Functions can take other functions as arguments. You can put a function on a stack with & for example `&add`. If a function doesn't have a name then it's put on the stack automatically. You can run the function value with .go:
```
@processPrint[str,[str][str]]
    .go .pr
;

"Hello" @[str][str] ,1 "Hi"; .processPrint
``` 
- You can make function's type the same as an other function's type with `:`:
```
@add3[int,int,int][int]
    .add .add
;
@sub3:add3
    .sub .sub
;
```
- parameters and return values can be generic:
```
@swap[1,2][2,1]
    <>1
;
```

### Conditions
```
condition ?
true_branch :
false_branch $
```
Condition can be 0 for false or any other integer for true. Both branches must produce the same stack.

### External functions

- You can define external functions as follows (provided that you link them):
```
!BeginDrawing[]
!EndDrawing[]
!WindowShouldClose[][int]
!SetTargetFPS[int]
!ClearBackground[int]
!DrawText[int,int,int,int,str]
!DrawCircle[int,int,float,int]
```