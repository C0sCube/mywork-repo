n : float  =1.25
n2: complex = 4 + 7j
# print(abs(n)) #get absolute

voters: list[int] = [1,0,1,1,0,1]
voters2: list[int] = [0,0,0,0,0]

# print(all(voters), all(voters2))
# print(any(voters), any(voters2))

#ascii chars

text: str = "H%llo am i working"
#print(ascii(text))

#print(chr(30))


pairs: list[tuple[str,int]] = [('a',1),('b',2)]
#print(pairs)
 

#DIR METHOD
#print(dir('hello'))

listr = ['kaustubh','keny','mahesh','suresh']

for i, member in enumerate(listr, start=1):
    print(i, member, sep=": ")
    

some_text: str = "10 + 45 + 10"
print(eval(some_text))
