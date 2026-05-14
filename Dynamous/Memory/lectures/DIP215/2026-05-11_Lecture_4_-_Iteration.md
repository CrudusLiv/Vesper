---
type: lecture
course: DIP215
source_file: Lecture_4_-_Iteration.pptx
date: 2026-05-11
tags: [lecture, DIP215, iteration, loops]
---

# Lecture 4: Program Control Flow - Iteration

## Key concepts
- Flow of control: order statements execute (sequential, conditional, iterative)
- Three iteration constructs in Java: while, for, do-while
- Loop structure: initialization, testing condition, loop body, update
- Counter-controlled loop: uses a counter variable to determine when to stop
- Sentinel-controlled loop: terminates when special input value is entered
- Increment operators: `num++` equivalent to `num = num + 1`; compound operators like `+=`
- do-while executes loop body at least once (test happens after)
- for loop is cleaner syntax for counter-controlled loops
- Infinite loops occur when counter is never updated

## Worked examples

While loop example:
```java
int num = 0;
while (num < 10) {
    System.out.println("The value of num is " + num);
    num = num + 1;
}
System.out.println("The End");
```

Counter-controlled while loop with user input:
```java
Scanner keyboard = new Scanner(System.in);
System.out.print("Limit? ");
int limit = keyboard.nextInt();
int i = 1;
while (i <= limit) {
    System.out.println(i);
    i++;
}
```

Accumulating scores example:
```java
import java.util.*;
public class Results {
    public static void main(String[] args) {
        Scanner input = new Scanner(System.in);
        double total = 0.0;
        double score;
        int numAssignments;
        
        System.out.print("How many assignments? ");
        numAssignments = input.nextInt();
        int count = 1;
        while (count <= numAssignments) {
            System.out.print("Enter score for assignment");
            System.out.println(count + ": ");
            score = input.nextDouble();
            total = total + score;
            count++;
        }
        
        double average = total / numAssignments;
        System.out.println("The Total is " + total);
        System.out.println("Average score is " + average);
    }
}
```

Sentinel-controlled while loop:
```java
System.out.print("Do you understand?");
Scanner keyboard = new Scanner(System.in);
char answer;
answer = keyboard.next().charAt(0);
while (answer == 'N' || answer == 'n') {
    System.out.println("I will explain again");
    System.out.println("blah blah blah..");
    System.out.print("NOW do you understand?");
    answer = keyboard.next().charAt(0);
}
System.out.println("Good!");
```

For loop vs while loop equivalence:
```java
// While loop
int i = 1;
while (i <= 5) {
    System.out.println(i);
    i++;
}

// Equivalent for loop
for(int i = 1; i <= 5; i++)
    System.out.println(i);
```

Printing even numbers 1-100:
```java
public class PrintAllEven {
    public static void main(String[] args) {
        System.out.println("Even numbers between 1 and 100");
        for (int i = 2; i <= 100; i+=2) {
            System.out.println(i);
        }
    }
}
```

Formatting output (5 numbers per line):
```java
int count = 0;
for (int i = 2; i <= 100; i+=2) {
    System.out.print(i + " ");
    count++;
    if (count == 5) {
        System.out.println();
        count = 0;
    }
}
```

Sum of integers 1 to n:
```java
Scanner keyboard = new Scanner(System.in);
int sum = 0;
System.out.print("what is the limit?");
int limit = keyboard.nextInt();
for (int i = 1; i <= limit; i++) {
    sum += i;
}
if (limit > 0)
    System.out.println("The sum is " + sum);
else
    System.out.println("You must enter a positive number");
```

do-while loop example:
```java
Scanner sc = new Scanner(System.in);
System.out.print("Limit? ");
int limit = sc.nextInt();
int i = 1;
do {
    System.out.println(i);
    i++;
} while (i <= limit);
System.out.println("End");
```

## Study cards
- Q: What are the three types of loop constructs in Java? | A: while, for, do-while
- Q: What are the three components of loop structure? | A: initialization, testing condition, update
- Q: What is the key difference between while and do-while loops? | A: do-while executes the loop body at least once; while may never execute if condition is false
- Q: When is a counter-controlled loop used vs. a sentinel-controlled loop? | A: Counter-controlled: know in advance how many iterations (counter variable); Sentinel-controlled: iterate until special value is entered
- Q: What does `num++` do? | A: Increments num by 1 (equivalent to `num = num + 1`)
- Q: When is a for loop preferred over a while loop? | A: When it is clearly a counter-controlled loop with known initialization, condition, and increment
- Q: What causes an infinite loop? | A: The loop condition is never made false, usually because the counter is not being updated
- Q: What is the syntax for a for loop? | A: `for (initialization; testing; update) { loop body }`
- Q: Why would you use a do-while loop to create a menu? | A: Because the menu needs to display at least once even if the condition would initially be false

## Open questions
- Why does a for loop line have no semicolon at the end?
- How do you choose between while, for, and do-while in real applications?
- What are nested loops and when would you use them?

<!-- related:begin -->
## Related
- [[2026-05-11_Lecture_3_-_Selection_Constructs]]
- [[2026-05-11_Lecture_5_-_Static_methods]]
- [[2026-05-11_Lecture_6_-_Object_Oriented_Programming]]
- [[2026-05-11_Lecture_7_-_Object-based_programming]]
<!-- related:end -->
