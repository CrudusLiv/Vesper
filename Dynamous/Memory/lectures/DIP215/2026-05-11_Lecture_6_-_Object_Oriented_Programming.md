```markdown
---
type: lecture
course: DIP215
source_file: Lecture_6_-_Object_Oriented_Programming.pptx
date: 2026-05-11
tags: [lecture, DIP215]
---

# Lecture 6 - Object-Oriented Programming

## Key concepts

- A programming paradigm is a fundamental style of computer programming; a guiding principle for how to write and organize code
- Three main paradigms: Object-Oriented (organizes code around objects with data and methods), Functional (functions that don't change data), Procedural (step-by-step procedures that change data)
- Abstraction: hiding internal implementation complexity and exposing only necessary interfaces
- Encapsulation: bundling data and methods in a class; uses access modifiers (public, protected, private) for information hiding
- Polymorphism: ability of different objects to respond to the same method call with type-specific behavior; includes overloading and late binding
- Inheritance: reusing code by creating subclasses that inherit attributes and behavior from superclasses; creates a class hierarchy
- A class is a blueprint/template defining abstract characteristics (attributes/fields) and behaviors (methods/operations)
- An object is an instance of a class, created at runtime through instantiation; has state (attribute values) and behavior
- Primitive data types (byte, short, int, long, float, double, char, boolean) store single values directly in memory
- Reference data types (classes like String) store memory addresses to objects; the actual object is allocated with the `new` operator
- String is a class type representing a sequence of characters; declare with `String name = new String("value");`

## Worked examples

String declaration and initialization:
```java
String subjectName = "Java";
String subjectCode = new String("BIT106");
```

String comparison (operators vs methods):
```java
String s1 = new String("hi");
String s2 = new String("hi");
String s3 = s2;

System.out.println(s1 == s2);           // false (different memory addresses)
System.out.println(s2 == s3);           // true (same memory address)
System.out.println(s1.equals(s2));      // true (same content)
System.out.println(s1.equalsIgnoreCase(s2));  // true
```

String methods example:
```java
String original = "Hello, World!";

// Length
System.out.println(original.length());  // 13

// Convert to lowercase
String lowercase = original.toLowerCase();  // "hello, world!"

// Replace
String updated = original.replace("World", "Java");  // "Hello, Java!"

// Check start/end
if (original.startsWith("Hello")) {
    System.out.println("Starts with 'Hello'");
}

if (original.endsWith("World!")) {
    System.out.println("Ends with 'World!'");
}

// Find index
int index = original.indexOf("o");  // 4
System.out.println(index);
```

Display string one character per line:
```java
String s = "Happy New Year";
for (int i = 0; i < s.length(); i++) {
    System.out.println(s.charAt(i));
}
```

PhoneCard class definition:
```java
public class PhoneCard {
    private String phoneNumber;
    private double balance;
    
    // Constructor
    public PhoneCard(String phoneNumber, double balance) {
        this.phoneNumber = phoneNumber;
        this.balance = balance;
    }
    
    // Getter methods
    public String getPhoneNumber() {
        return phoneNumber;
    }
    
    public double getBalance() {
        return balance;
    }
    
    // Setter methods
    public void setPhoneNumber(String newPhoneNum) {
        phoneNumber = newPhoneNum;
    }
    
    public void setBalance(double newBalance) {
        balance = newBalance;
    }
    
    // Business methods
    public void topUp(double amount) {
        balance += amount;
    }
    
    public boolean makeCall(double duration, double costPerMin) {
        double cost = duration * costPerMin;
        if (balance >= cost) {
            balance -= cost;
            return true;
        }
        return false;
    }
    
    public String toString() {
        return "PhoneCard: " + phoneNumber + ", Balance: RM" + balance;
    }
}
```

Creating and using PhoneCard objects:
```java
PhoneCard myCard = new PhoneCard("012-1122334", 20);
PhoneCard extraCard = new PhoneCard("012-1234567", 10);

System.out.println(extraCard.getBalance());  // 10
myCard.topUp(15);                             // balance becomes 35
myCard.makeCall(20, 0.30);                    // costs 6.00, balance becomes 29
```

## Study cards

- Q: What is a programming paradigm? | A: A fundamental style and guiding principle for how programs are constructed and how code should be organized to solve a problem.

- Q: How does Object-Oriented Programming differ from Procedural Programming? | A: OOP organizes code around objects with data and methods that interact together, while Procedural Programming uses step-by-step procedures that change data sequentially.

- Q: Define abstraction in OOP. | A: Abstraction hides internal implementation complexity and exposes only necessary interfaces; you interact with objects through simple interfaces without knowing how they work internally.

- Q: What does encapsulation mean and how is it implemented? | A: Encapsulation bundles data and methods into a class and uses access modifiers (public, protected, private) to control which members are accessible from outside the class.

- Q: What is the difference between a class and an object? | A: A class is a blueprint/template defining characteristics and behaviors; an object is an instance of a class created at runtime with its own state (attribute values).

- Q: Explain the difference between primitive and reference data types with memory allocation. | A: Primitive types store values directly in memory (e.g., int num = 12). Reference types store memory addresses to objects; the object itself is allocated with the `new` operator (e.g., String s = new String("Hello")).

- Q: Why does `s1 == s2` return false while `s1.equals(s2)` returns true for two different String objects with the same content? | A: The == operator compares memory addresses; it returns false because s1 and s2 point to different memory locations. The equals() method compares the actual string content, returning true because both contain the same characters.

- Q: What is a constructor and what does it do? | A: A constructor is a special method that creates and initializes a new object of a class; it has the same name as the class and runs when you use the `new` operator.

- Q: Name the four main principles of OOP. | A: Abstraction, Encapsulation, Polymorphism, and Inheritance.

- Q: What does inheritance allow you to do in OOP? | A: Inheritance allows you to create subclasses that reuse and extend the attributes and behaviors of existing superclasses, promoting code reuse and establishing a class hierarchy.

## Open questions

- How do you design a class hierarchy effectively for complex domains?
- What are the detailed rules for method overloading and how does it enable polymorphism?
- How do access modifiers (protected, private) work with inheritance?
- What is the full syntax and usage of toString() for custom objects?
- When should you use composition vs. inheritance?
```

Note ready for Obsidian. Key concepts cover the four OOP principles plus class/object distinction and String handling. Worked examples include all code snippets from the lecture. Study cards drill the most testable definitions and differences. Open questions flag topics hinted at but not fully covered.

<!-- related:begin -->
## Related
- [[2026-05-11_Lecture_3_-_Selection_Constructs]]
- [[2026-05-11_Lecture_4_-_Iteration]]
- [[2026-05-11_Lecture_5_-_Static_methods]]
- [[2026-05-11_Lecture_7_-_Object-based_programming]]
<!-- related:end -->
