---
type: lecture
course: DIP215
source_file: Lecture_5_-_Static_methods.pptx
date: 2026-05-11
tags: [lecture, DIP215]
---

# Lecture 5: Methods

## Key concepts
- **Functional decomposition**: breaking large programs into separate, independent methods with specific purposes
- **Method structure**: four essential parts are return type, meaningful name, parameter list, and body
- **Method header**: specifies the method's input (parameters), output (return type), and purpose
- **Static methods**: belong to a class and do not require an object to invoke; used for operations with no meaningful connection to an object (e.g., finding max, computing square root)
- **Access modifiers**: public (accessible outside the class), private, protected, static
- **Arguments/parameters**: provide input data to methods; must match in number, type, and order when invoked
- **Method overloading**: creating multiple methods with the same name but different method headers
- **Return types**: indicate the type of data returned (or `void` if nothing is returned)
- **Advantages of methods**: smaller, more readable main method; easier debugging; code reuse; modularity; portability across programs
- **Method invocation**: control passes from caller to method; static methods in other classes are invoked using ClassName.methodName()

## Worked examples

**Method structure example:**

```java
double calcCost(double uPrice, int qty)
{
    double cost = uPrice * qty;
    return cost;
}
```

**Static method definition and invocation:**

```java
public class Star
{
    public static void main(String[] args)
    {
        System.out.println("Here is a line of stars");
        printStars();
        System.out.println("Here is another!");
        printStars();
    }
    
    public static void printStars()
    {
        System.out.println("***********************");
    }
}
```

**Invoking static method from another class:**

```java
public class PrintName
{
    public static void main(String[] args)
    {
        System.out.println("My name is Jane!");
        Star.printStars();  // ClassName.methodName()
    }
}
```

**Method overloading:**

```java
public static void printStars()
{
    System.out.println("***********************");
}

public static void printStars(int n)
{
    // prints a line of n stars
}
```

**Using returned data:**

```java
double price = 2.50;
System.out.println("The cost of 3 items " + cost(price, 3));

int number = sc.nextInt();
double totalCost = cost(price, number);
System.out.println("The cost of " + number + " items is " + totalCost);

public static double cost(double uPrice, int qty)
{
    return uPrice * qty;
}
```

## Study cards

- Q: What are the four parts of a Java method? | A: Return type, meaningful name, parameter list, and body

- Q: What is a static method? | A: A method that belongs to a class and does not require an object to be invoked; used for operations unrelated to specific objects

- Q: How do you invoke a static method from another class? | A: Use the class name followed by a dot and the method name: ClassName.methodName()

- Q: What does the return type indicate? | A: The type of data returned by the method

- Q: What does void return type mean? | A: The method does not return any value

- Q: What is method overloading? | A: Creating two or more methods with the same name but different method headers (different parameters)

- Q: What must match when invoking a method with arguments? | A: The number, type, and order of arguments must match the method's parameter list

- Q: Name three advantages of using methods in programs. | A: Main method is smaller and more readable; methods can be debugged separately; code reuse without duplication; methods can be modified independently; methods may be used by other programs

- Q: What is functional decomposition? | A: Breaking down a large program into smaller, separate methods each with a specific purpose

- Q: What is the purpose of a method header? | A: To specify the method's input (parameters), output (return type), and indicate its purpose

## Open questions

- When should a method be declared static versus as an instance method?
- How do private and protected access modifiers differ in their restrictions?
- What are best practices for naming methods?
- How does the Math class implement its methods as static?
- What happens if a method's return type doesn't match the type of value returned?

<!-- related:begin -->
## Related
- [[2026-05-11_Lecture_3_-_Selection_Constructs]]
- [[2026-05-11_Lecture_4_-_Iteration]]
- [[2026-05-11_Lecture_6_-_Object_Oriented_Programming]]
- [[2026-05-11_Lecture_7_-_Object-based_programming]]
<!-- related:end -->
