---
type: lecture
course: DIP103
source_file: Chapter8_Logic_Modeling_2023.pptx
date: 2026-05-14
tags: [lecture, DIP103]
---

# Chapter 8: Logic Modeling

## Key concepts
- Data dictionaries are metadata repositories that catalog and standardize data terminology across projects
- Algebraic notation (=, +, {}, [], ()) provides formal syntax for describing data structure composition
- Process specifications (minispecs) reduce ambiguity, provide precise descriptions, and validate system design
- Structured decisions are distinguishable from semistructured decisions and benefit from systematic analysis
- Three complementary logic modeling methods exist: Structured English, Decision Tables, Decision Trees

## Worked examples

### Algebraic Notation for Data Structures
```
= means "is composed of"
+ means "and"
{} means repetitive elements
[] means either/or (mutually exclusive)
() means optional elements
```

Example: CUSTOMER_ORDER = CUSTOMER_INFO + {ITEM_RECORD} + (SPECIAL_REQUEST)

### Structured English Syntax
```
IF condition THEN
   statement
ELSE
   statement
END IF

DO WHILE condition
   statement
PERFORM UNTIL condition
   statement
```

### Decision Table Structure
Four quadrants:
- Upper left: Conditions
- Upper right: Condition alternatives
- Lower left: Actions to be taken
- Lower right: Rules for executing actions (marked with X)

### Decision Tree Structure
- Root (leftmost), branches extend rightward
- Each node represents a condition
- Each branch represents an alternative
- Terminal nodes represent actions
- Not symmetrical; branches may vary in depth and complexity

## Study cards

- Q: What is a data dictionary? | A: A reference work of metadata (data about data) that collects, coordinates, and standardizes data terms to ensure consistency across projects and eliminate discrepancies like storing gender as "M", "male", or "1"

- Q: Name five benefits of maintaining a data dictionary. | A: Avoid data inconsistencies; define project conventions; ensure consistency across analyst teams; make data easier to analyze; enforce data standards

- Q: What do the four algebraic notation symbols mean? | A: = (is composed of), + (and), {} (repetitive/repeating groups), [] (either/or/mutually exclusive), () (optional)

- Q: What are the three basic constructs in process logic? | A: Sequence (MOVE, ADD, SUBTRACT), Selection (IF...THEN...ELSE from [] entries), Iteration (DO WHILE, DO UNTIL from {} entries)

- Q: What is a process specification and what are its three main goals? | A: A minspec describing decision-making logic and formulas that transform input to output; goals are to reduce process ambiguity, obtain precise descriptions of accomplishments, and validate system design

- Q: Name four main problems to check for when validating a decision table. | A: Incompleteness (missing conditions), Impossible situations (contradictory conditions), Contradictions (same conditions requiring different actions), Redundancy (identical alternatives requiring same action)

- Q: When should you use Structured English versus a Decision Table? | A: Use Structured English when there are repetitious actions or communication to end users is critical; use Decision Tables when complex combinations of conditions, actions, and rules exist and you need to detect impossible situations and contradictions

- Q: When should you use a Decision Tree? | A: When the sequence of conditions and actions is critical, when not every condition is relevant to every action (different branches), or when proper sequencing is essential

- Q: How are data flow diagrams, data dictionaries, and process specifications related? | A: DFDs identify processes and data flows; the data dictionary describes data flows and stores in detail; process specifications explain the decision logic and formulas for each process, linking DFD to data dictionary

- Q: What should business rule descriptions in process specifications address? | A: Definitions of business terms, business conditions and actions, data integrity constraints, mathematical and functional derivations, logical inferences, processing sequences, and relationships among business facts

## Open questions
- How are automated data dictionaries implemented in modern systems and what tools support them?
- What is the relationship between data standards enforcement and RDBMS referential integrity?
- How do decision table processors convert tables into executable code?
- When multiple decision analysis methods could apply to a single process, how is the best choice determined in practice?