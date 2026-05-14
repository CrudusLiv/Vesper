---
type: lecture
course: DIP215
source_file: Lecture 3 - Selection Constructs.pptx
date: 2026-05-11
tags: [lecture, DIP215, selection, control-flow, java]
---

# Lecture 3: Program Control Flow - Selection Constructs

## Key concepts
- Flow of control: the order in which a program processes statements—sequentially, conditionally, or repetitively
- Selection (branching) statements determine which path the computer should take based on a decision point
- Boolean expressions evaluate to true or false and drive selection logic
- Comparison operators: `==`, `!=`, `<`, `>`, `<=`, `>=` used in boolean expressions
- Logical operators: `&&` (AND), `||` (OR), `!` (NOT) combine boolean expressions
- The if-else statement executes statement_1 if the condition is true, otherwise statement_2
- Omitting the else clause: if condition is false, no action occurs
- Compound statements: multiple statements enclosed in braces `{}` act as a single statement
- Nested if statements: if-else blocks can be placed inside other if-else blocks; each else pairs with the nearest unmatched if
- Multi-branch if-else: multiple conditions tested in sequence with `else if`
- Switch statement: a multiway branch for integral (integer/character) expressions; cleaner than nested if-else for many cases
- Each `case` in a switch must end with `break;` to prevent fall-through
- Character encoding: Java uses Unicode (16 bits, 65536 symbols); first 256 match ASCII; characters have numerical codes ('0'=48, 'A'=65, 'a'=97)

## Worked examples

### Voter eligibility program
```java
import java.util.*;

public class Voter {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        System.out.println("Enter your year of birth :");
        int yearOfBirth = sc.nextInt();
        int age = 2023 - yearOfBirth;
        
        if (age < 21)
            System.out.println("too young to vote");
        else
            System.out.println("register as voter");
    }
}
```

### Late assignment penalty
```java
System.out.println("Enter raw marks :");
marks = sc.nextDouble();
System.out.println("How many days late?");
numDaysLate = sc.nextInt();

if (numDaysLate > 0) {
    marks = marks - (numDaysLate * 5);
}
System.out.println("Final mark : " + marks);
```

### Character input for gender (multi-branch if-else)
```java
public static void main(String[] args) {
    Scanner sc = new Scanner(System.in);
    System.out.print("Enter your name: ");
    String name = sc.nextLine();
    System.out.print("Are you (m)ale or (f)emale :");
    char gender = sc.next().charAt(0);
    
    if (gender == 'm' || gender == 'M')
        System.out.print("Hello, Mr." + name);
    else if (gender == 'f' || gender == 'F')
        System.out.print("Hello, Ms. " + name);
    else
        System.out.println("Hello, " + name);
}
```

### Nested if for year-based passing mark
```java
if (year == 1)
    if (mark >= 50)
        System.out.println("Pass");
    else
        System.out.println("Fail");
else if (year == 2)
    if (mark >= 60)
        System.out.println("Pass");
    else
        System.out.println("Fail");
else if (year == 3)
    if (mark >= 40)
        System.out.println("Pass");
    else
        System.out.println("Fail");
else
    System.out.println("Cannot be determined");
```

### Switch statement for gender
```java
switch (gender) {
    case 'm': case 'M':
        System.out.println("Hello, Mr. " + name);
        break;
    case 'f': case 'F':
        System.out.println("Hello, Ms. " + name);
        break;
    default:
        System.out.println("Hello, " + name);
        break;
}
```

### Math class example
```java
int num = 16;
System.out.println("The square root of " + num);
System.out.println("is " + Math.sqrt(num));
```

## Logical operator truth table
For boolean expressions P and Q:

| P | Q | P && Q | P \|\| Q | !P |
|---|---|--------|----------|-----|
| T | T | T      | T        | F   |
| T | F | F      | T        | F   |
| F | T | F      | T        | T   |
| F | F | F      | F        | T   |

## Operator precedence (highest to lowest)
1. Parentheses / brackets: `( )`
2. Type cast: `(type)`
3. Logical NOT: `!`
4. Arithmetic: `*`, `/`, `%`
5. Arithmetic: `+`, `–`
6. Relational: `>`, `>=`, `<`, `<=`, `==`, `!=`
7. Logical AND: `&&`
8. Logical OR: `||`

## Switch statement syntax
```java
switch (variable / expression) {
    case label1:
        statement1;
        break;
    case label2:
    case label3:
        statement2;
        statement3;
        break;
    case label4: case label5:
        statement4;
        break;
    default:
        statement5;
        break;
}
```

## Study cards

- Q: What is the syntax of an if-else statement? | A: `if (boolean_expression) { statement_1; } else { statement_2; }`

- Q: What are the three types of flow of control? | A: Sequential (line by line), conditional (branching), and repetitive (loops)

- Q: What does `&&` (AND) return? | A: True only if both operands are true; false otherwise

- Q: What does `||` (OR) return? | A: True if at least one operand is true; false only if both are false

- Q: What is the effect of omitting the `else` clause in an if statement? | A: If the condition is false, no action occurs and execution continues after the if block

- Q: How does each `else` pair with an `if` in nested statements? | A: Each else pairs with the nearest unmatched if above it

- Q: When should you use a `switch` statement instead of nested if-else? | A: When testing a single integral (integer or character) expression against many constant values; it is cleaner and often clearer

- Q: What does the `break;` statement do in a switch case? | A: It exits the switch block; without it, execution falls through to the next case

- Q: What is the Unicode value of the character 'A'? | A: 65

- Q: Can you compare characters using `<` and `>` operators in Java? Why or why not? | A: Yes, because characters have numerical Unicode values ('3' < '9' is true because 51 < 57)

## Open questions
- When is fall-through behavior in switch statements intentional versus a bug?
- How do performance characteristics compare between deeply nested if-else and switch statements?
- What are best practices for choosing between multi-branch if-else and switch?
- How do compound conditions affect readability versus performance?

<!-- related:begin -->
## Related
- [[2026-05-11_Lecture_4_-_Iteration]]
- [[2026-05-11_Lecture_5_-_Static_methods]]
- [[2026-05-11_Lecture_6_-_Object_Oriented_Programming]]
- [[2026-05-11_Lecture_7_-_Object-based_programming]]
<!-- related:end -->
